from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.db.allowlist import list_active_role_keys
from backend.models import (
    AllowlistColumn,
    AllowlistTable,
    MetricDefinition,
    SemanticColumn,
    SemanticVisibilityOverrideRequest,
)
from backend.semantic.llm import LLMClient


NUMERIC_HINTS = {"int", "decimal", "numeric", "float", "double", "bigint", "smallint"}
TIME_HINTS = {"date", "time", "timestamp", "datetime", "year"}


class SemanticService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def build_semantic_model(
        self,
        session: Session,
        organization_id: str,
        data_source_id: str,
        schema_json: Dict[str, Any],
        allowlist: Dict[str, set[str]],
    ) -> Dict[str, Any]:
        session.execute(
            delete(SemanticColumn).where(
                SemanticColumn.organization_id == organization_id,
                SemanticColumn.data_source_id == data_source_id,
            )
        )
        session.execute(
            delete(MetricDefinition).where(
                MetricDefinition.organization_id == organization_id,
                MetricDefinition.data_source_id == data_source_id,
            )
        )

        role_catalog = list_active_role_keys(session, organization_id)
        visibility_map = self._load_allowlist_visibility(session, data_source_id)

        semantic_columns: List[Dict[str, Any]] = []
        metrics: List[Dict[str, Any]] = []

        for db_entry in schema_json.get("databases", []):
            db_name = db_entry["database_name"]
            for table in db_entry.get("tables", []):
                table_name = table["table_name"]
                fq_table = f"{db_name}.{table_name}"
                approved_columns = allowlist.get(fq_table)
                if not approved_columns:
                    continue

                for col in table.get("columns", []):
                    col_name = col["name"]
                    if col_name not in approved_columns:
                        continue

                    semantic_type = self._classify_column(col_name, col.get("type", ""))
                    description = self._column_description(table_name, col_name, semantic_type)
                    metric_candidates = self._metric_candidates(col_name, semantic_type)
                    column_roles = self._column_roles(visibility_map, fq_table, col_name, role_catalog)

                    session.add(
                        SemanticColumn(
                            organization_id=organization_id,
                            data_source_id=data_source_id,
                            database_name=db_name,
                            table_name=table_name,
                            column_name=col_name,
                            semantic_type=semantic_type,
                            description=description,
                            metric_candidates=metric_candidates,
                            allowed_roles=column_roles,
                        )
                    )
                    semantic_columns.append(
                        {
                            "database_name": db_name,
                            "table_name": table_name,
                            "column_name": col_name,
                            "semantic_type": semantic_type,
                            "description": description,
                            "metric_candidates": metric_candidates,
                            "allowed_roles": column_roles,
                        }
                    )

                    for metric_name, metric_sql in self._default_metrics(db_name, table_name, col_name, semantic_type):
                        metric_roles = self._default_metric_visibility(metric_name, col_name, table_name, role_catalog)
                        metric_roles = [r for r in metric_roles if r in column_roles]
                        if not metric_roles:
                            metric_roles = column_roles

                        metric = {
                            "name": metric_name,
                            "description": f"Default metric generated for {db_name}.{table_name}.{col_name}",
                            "expression_sql": metric_sql,
                            "metadata": {
                                "database_name": db_name,
                                "table_name": table_name,
                                "column_name": col_name,
                            },
                            "allowed_roles": metric_roles,
                        }
                        metrics.append(metric)

        unique_metrics = {m["name"]: m for m in metrics}
        for m in unique_metrics.values():
            session.add(
                MetricDefinition(
                    organization_id=organization_id,
                    data_source_id=data_source_id,
                    name=m["name"],
                    description=m["description"],
                    expression_sql=m["expression_sql"],
                    meta=m["metadata"],
                    allowed_roles=m["allowed_roles"],
                )
            )

        return self.get_semantics(session, organization_id, data_source_id)

    def get_semantics(self, session: Session, organization_id: str, data_source_id: str) -> Dict[str, Any]:
        columns = session.scalars(
            select(SemanticColumn).where(
                SemanticColumn.organization_id == organization_id,
                SemanticColumn.data_source_id == data_source_id,
            )
        ).all()
        metrics = session.scalars(
            select(MetricDefinition).where(
                MetricDefinition.organization_id == organization_id,
                MetricDefinition.data_source_id == data_source_id,
            )
        ).all()

        table_rows = session.scalars(select(AllowlistTable).where(AllowlistTable.data_source_id == data_source_id)).all()
        semantic_tables = []
        for table in table_rows:
            table_columns = session.scalars(select(AllowlistColumn).where(AllowlistColumn.allowlist_table_id == table.id)).all()
            semantic_tables.append(
                {
                    "database_name": table.database_name,
                    "table_name": table.table_name,
                    "allowed_roles": table.allowed_roles or [],
                    "columns": [
                        {"column_name": c.column_name, "allowed_roles": c.allowed_roles or []}
                        for c in table_columns
                    ],
                }
            )

        return {
            "semantic_tables": semantic_tables,
            "semantic_columns": [
                {
                    "database_name": c.database_name,
                    "table_name": c.table_name,
                    "column_name": c.column_name,
                    "semantic_type": c.semantic_type,
                    "description": c.description,
                    "metric_candidates": c.metric_candidates,
                    "allowed_roles": c.allowed_roles or [],
                }
                for c in columns
            ],
            "metrics": [
                {
                    "name": m.name,
                    "description": m.description,
                    "expression_sql": m.expression_sql,
                    "metadata": m.meta,
                    "allowed_roles": m.allowed_roles or [],
                }
                for m in metrics
            ],
        }

    def get_role_aware_semantics(self, session: Session, organization_id: str, data_source_id: str, role: str) -> Dict[str, Any]:
        semantics = self.get_semantics(session, organization_id, data_source_id)

        def visible(item: Dict[str, Any]) -> bool:
            roles = item.get("allowed_roles") or []
            return (not roles) or (role in roles)

        return {
            "semantic_tables": [t for t in semantics.get("semantic_tables", []) if visible(t)],
            "semantic_columns": [c for c in semantics.get("semantic_columns", []) if visible(c)],
            "metrics": [m for m in semantics.get("metrics", []) if visible(m)],
        }

    def apply_visibility_overrides(
        self,
        session: Session,
        organization_id: str,
        data_source_id: str,
        payload: SemanticVisibilityOverrideRequest,
    ) -> Dict[str, Any]:
        for t in payload.table_overrides:
            table = session.scalars(
                select(AllowlistTable).where(
                    AllowlistTable.data_source_id == data_source_id,
                    AllowlistTable.database_name == t.database_name,
                    AllowlistTable.table_name == t.table_name,
                )
            ).first()
            if table:
                table.allowed_roles = t.allowed_roles

        for c in payload.column_overrides:
            table = session.scalars(
                select(AllowlistTable).where(
                    AllowlistTable.data_source_id == data_source_id,
                    AllowlistTable.database_name == c.database_name,
                    AllowlistTable.table_name == c.table_name,
                )
            ).first()
            if not table:
                continue
            col = session.scalars(
                select(AllowlistColumn).where(
                    AllowlistColumn.allowlist_table_id == table.id,
                    AllowlistColumn.column_name == c.column_name,
                )
            ).first()
            if col:
                col.allowed_roles = c.allowed_roles

            semantic_col = session.scalars(
                select(SemanticColumn).where(
                    SemanticColumn.organization_id == organization_id,
                    SemanticColumn.data_source_id == data_source_id,
                    SemanticColumn.database_name == c.database_name,
                    SemanticColumn.table_name == c.table_name,
                    SemanticColumn.column_name == c.column_name,
                )
            ).first()
            if semantic_col:
                semantic_col.allowed_roles = c.allowed_roles

        for m in payload.metric_overrides:
            metric = session.scalars(
                select(MetricDefinition).where(
                    MetricDefinition.organization_id == organization_id,
                    MetricDefinition.data_source_id == data_source_id,
                    MetricDefinition.name == m.metric_name,
                )
            ).first()
            if metric:
                metric.allowed_roles = m.allowed_roles

        return self.get_semantics(session, organization_id, data_source_id)

    def detect_restricted_metric_request(
        self,
        session: Session,
        organization_id: str,
        data_source_id: str,
        role: str,
        question: str,
    ) -> bool:
        question_l = question.lower()
        metrics = session.scalars(
            select(MetricDefinition).where(
                MetricDefinition.organization_id == organization_id,
                MetricDefinition.data_source_id == data_source_id,
            )
        ).all()

        restricted_hits = 0
        visible_hits = 0
        for metric in metrics:
            name_l = metric.name.lower().replace("_", " ")
            desc_l = metric.description.lower()
            matched = any(token in question_l for token in self._important_tokens(name_l + " " + desc_l))
            if not matched:
                continue

            allowed = metric.allowed_roles or []
            if allowed and role not in allowed:
                restricted_hits += 1
            else:
                visible_hits += 1

        return restricted_hits > 0 and visible_hits == 0

    def _load_allowlist_visibility(self, session: Session, data_source_id: str) -> Dict[str, Any]:
        tables = session.scalars(select(AllowlistTable).where(AllowlistTable.data_source_id == data_source_id)).all()
        table_roles: Dict[str, List[str]] = {}
        column_roles: Dict[str, Dict[str, List[str]]] = {}

        for table in tables:
            fq_table = f"{table.database_name}.{table.table_name}"
            table_roles[fq_table] = table.allowed_roles or []
            cols = session.scalars(select(AllowlistColumn).where(AllowlistColumn.allowlist_table_id == table.id)).all()
            column_roles[fq_table] = {c.column_name: (c.allowed_roles or []) for c in cols}

        return {"table_roles": table_roles, "column_roles": column_roles}

    def _column_roles(self, visibility_map: Dict[str, Any], fq_table: str, column_name: str, role_catalog: List[str]) -> List[str]:
        table_roles = visibility_map.get("table_roles", {}).get(fq_table) or role_catalog
        column_roles = visibility_map.get("column_roles", {}).get(fq_table, {}).get(column_name) or table_roles
        return [r for r in column_roles if r in role_catalog] or role_catalog

    def _classify_column(self, column_name: str, db_type: str) -> str:
        c = column_name.lower()
        t = db_type.lower()
        if any(k in t for k in TIME_HINTS) or any(k in c for k in ["date", "time", "month", "year", "day"]):
            return "time_dimension"
        if any(k in t for k in NUMERIC_HINTS):
            if any(k in c for k in ["id", "code", "zip", "phone"]):
                return "dimension"
            return "measure"
        return "dimension"

    def _column_description(self, table_name: str, column_name: str, semantic_type: str) -> str:
        if not self.llm_client.is_configured():
            return f"{column_name} in {table_name} categorized as {semantic_type}."

        try:
            res = self.llm_client.complete_json(
                "You generate concise BI metadata.",
                (
                    "Return JSON with key 'description'. "
                    f"Table: {table_name}, Column: {column_name}, Semantic Type: {semantic_type}."
                ),
            )
            return str(res.get("description", "")).strip() or f"{column_name} in {table_name}."
        except Exception:
            return f"{column_name} in {table_name} categorized as {semantic_type}."

    def _metric_candidates(self, column_name: str, semantic_type: str) -> Dict[str, bool]:
        return {
            "sum": semantic_type == "measure",
            "count": True,
            "count_distinct": semantic_type in {"measure", "dimension"} and not column_name.lower().endswith("_amount"),
        }

    def _default_metrics(self, db_name: str, table_name: str, col_name: str, semantic_type: str) -> list[tuple[str, str]]:
        metrics = [(f"{table_name}_count", f"SELECT COUNT(*) AS {table_name}_count FROM {db_name}.{table_name}")]
        if semantic_type == "measure":
            metrics.append(
                (
                    f"{table_name}_{col_name}_sum",
                    f"SELECT SUM({col_name}) AS {table_name}_{col_name}_sum FROM {db_name}.{table_name}",
                )
            )
        metrics.append(
            (
                f"{table_name}_{col_name}_count_distinct",
                f"SELECT COUNT(DISTINCT {col_name}) AS {table_name}_{col_name}_count_distinct FROM {db_name}.{table_name}",
            )
        )
        return metrics

    def _default_metric_visibility(
        self,
        metric_name: str,
        column_name: str,
        table_name: str,
        role_catalog: List[str],
    ) -> List[str]:
        seed = f"{metric_name} {column_name} {table_name}".lower()
        if any(k in seed for k in ["revenue", "amount", "profit", "margin", "cost", "gmv", "arr"]):
            return [r for r in ["finance", "admin"] if r in role_catalog] or role_catalog
        if any(k in seed for k in ["unit", "quantity", "volume", "sold"]):
            preferred = ["sales", "executive", "admin"]
            return [r for r in preferred if r in role_catalog] or role_catalog
        preferred = ["admin", "executive", "senior_executive", "finance", "sales"]
        return [r for r in preferred if r in role_catalog] or role_catalog

    def _important_tokens(self, text: str) -> List[str]:
        tokens = []
        for token in text.replace("_", " ").split():
            token = token.strip().lower()
            if len(token) >= 4 and token not in {"count", "metric", "table", "from", "default", "generated", "column"}:
                tokens.append(token)
        return list(dict.fromkeys(tokens))
