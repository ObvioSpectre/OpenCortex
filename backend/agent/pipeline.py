from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from sqlalchemy.orm import Session

from backend.agent.insights import generate_insight
from backend.agent.intent import extract_intent
from backend.agent.sql_generator import SQLGenerator
from backend.agent.sql_validator import SQLValidationError, validate_sql
from backend.db.allowlist import get_data_source, get_role_scoped_allowlist
from backend.db.mysql import execute_readonly_query, get_mysql_engine
from backend.semantic.service import SemanticService
from backend.vector.service import VectorIndexService


@dataclass
class QueryPipeline:
    vector_index: VectorIndexService
    sql_generator: SQLGenerator
    semantic_service: SemanticService = field(default_factory=SemanticService)

    def run(
        self,
        session: Session,
        user_id: str,
        organization_id: str,
        role: str,
        data_source_id: str,
        question: str,
        show_sql: bool = False,
    ) -> Dict[str, Any]:
        data_source = get_data_source(session, data_source_id)
        if data_source is None:
            raise ValueError(f"Unknown data source {data_source_id}")
        if data_source.organization_id != organization_id:
            raise ValueError("Data source does not belong to provided organization_id")

        allowlist = get_role_scoped_allowlist(session, data_source_id, role=role)
        if not allowlist:
            return self._access_denied_response(
                question=question,
                organization_id=organization_id,
                user_id=user_id,
                role=role,
                data_source_id=data_source_id,
                denial_reason="No role-scoped table/column access available",
            )

        intent = extract_intent(question)
        if self.semantic_service.detect_restricted_metric_request(
            session=session,
            organization_id=organization_id,
            data_source_id=data_source_id,
            role=role,
            question=question,
        ):
            return self._access_denied_response(
                question=question,
                organization_id=organization_id,
                user_id=user_id,
                role=role,
                data_source_id=data_source_id,
                denial_reason="Requested metric is restricted for role",
            )

        collection = f"org:{organization_id}:semantic:{data_source_id}"
        retrieved_docs = self.vector_index.search(collection=collection, query=question, top_k=12, role=role)
        accessed_metrics = sorted({d.get("name") for d in retrieved_docs if d.get("kind") == "metric" and d.get("name")})

        sql_output = self.sql_generator.generate(question=question, intent=intent, retrieved_docs=retrieved_docs, allowlist=allowlist)
        sql = sql_output["sql"]

        try:
            validate_sql(sql, allowlist)
        except SQLValidationError:
            return self._sql_blocked_response(
                question=question,
                organization_id=organization_id,
                user_id=user_id,
                role=role,
                data_source_id=data_source_id,
                metrics_accessed=accessed_metrics,
            )

        engine = get_mysql_engine(data_source_id, data_source.mysql_uri)
        rows = execute_readonly_query(engine, sql)
        insight = generate_insight(question, rows)

        return {
            "question": question,
            "sql": sql if show_sql else None,
            "rows": rows,
            "insight": insight,
            "debug": {
                "auth_context": {"organization_id": organization_id, "role": role},
                "intent": intent,
                "semantic_hits": len(retrieved_docs),
                "sql_rationale": sql_output.get("rationale"),
            },
            "_audit": {
                "organization_id": organization_id,
                "user_id": user_id,
                "role": role,
                "data_source_id": data_source_id,
                "question": question,
                "metrics_accessed": accessed_metrics,
                "access_denied": False,
                "denial_reason": None,
            },
        }

    def _access_denied_response(
        self,
        question: str,
        organization_id: str,
        user_id: str,
        role: str,
        data_source_id: str,
        denial_reason: str,
    ) -> Dict[str, Any]:
        return {
            "question": question,
            "sql": None,
            "rows": [],
            "insight": {
                "executive_summary": "I can't provide that data right now.",
                "key_insights": ["This request couldn't be completed with the current access policy."],
                "recommendations": ["Try a different business question or contact an administrator for assistance."],
                "limitations": "Data access policy prevented query execution.",
            },
            "debug": {
                "auth_context": {"organization_id": organization_id, "role": role},
                "intent": {},
                "semantic_hits": 0,
                "sql_rationale": "Access denied by semantic visibility policy.",
            },
            "_audit": {
                "organization_id": organization_id,
                "user_id": user_id,
                "role": role,
                "data_source_id": data_source_id,
                "question": question,
                "metrics_accessed": [],
                "access_denied": True,
                "denial_reason": denial_reason,
            },
        }

    def _sql_blocked_response(
        self,
        question: str,
        organization_id: str,
        user_id: str,
        role: str,
        data_source_id: str,
        metrics_accessed: list[str],
    ) -> Dict[str, Any]:
        return {
            "question": question,
            "sql": None,
            "rows": [],
            "insight": {
                "executive_summary": "I can't provide that data right now.",
                "key_insights": ["The request could not be completed under current data access policy."],
                "recommendations": ["Try a different business question or contact an administrator for assistance."],
                "limitations": "SQL access guardrail blocked execution.",
            },
            "debug": {
                "auth_context": {"organization_id": organization_id, "role": role},
                "intent": {},
                "semantic_hits": 0,
                "sql_rationale": "Blocked by SQL validation guardrail.",
            },
            "_audit": {
                "organization_id": organization_id,
                "user_id": user_id,
                "role": role,
                "data_source_id": data_source_id,
                "question": question,
                "metrics_accessed": metrics_accessed,
                "access_denied": True,
                "denial_reason": "SQL validation guardrail blocked query",
            },
        }
