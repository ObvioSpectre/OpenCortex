from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Set

from backend.semantic.llm import LLMClient


class SQLGenerator:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def generate(
        self,
        question: str,
        intent: Dict[str, Any],
        retrieved_docs: List[Dict[str, Any]],
        allowlist: Dict[str, Set[str]],
    ) -> Dict[str, str]:
        selected = self._pick_table(question, retrieved_docs, allowlist)
        db_name, table_name = selected.split(".", 1)
        table_docs = [d for d in retrieved_docs if d.get("database_name") == db_name and d.get("table_name") == table_name]
        allowed_cols = allowlist[selected]

        time_col = self._pick_col(table_docs, allowed_cols, semantic_type="time_dimension")
        measure_col = self._pick_col(table_docs, allowed_cols, semantic_type="measure")
        dimension_col = self._pick_col(table_docs, allowed_cols, semantic_type="dimension")

        sql = self._build_sql(db_name, table_name, intent, allowed_cols, time_col, measure_col, dimension_col)
        rationale = f"Selected {selected} based on semantic retrieval and generated aggregation-first SQL."
        return {"sql": sql, "rationale": rationale}

    def _pick_table(self, question: str, docs: List[Dict[str, Any]], allowlist: Dict[str, Set[str]]) -> str:
        if docs:
            counts = defaultdict(int)
            for d in docs:
                db = d.get("database_name")
                t = d.get("table_name")
                if db and t:
                    fq = f"{db}.{t}"
                    if fq in allowlist:
                        counts[fq] += 1
            if counts:
                return max(counts, key=counts.get)

        q = question.lower()
        best = None
        best_score = -1
        for fq, columns in allowlist.items():
            db, table = fq.split(".", 1)
            score = int(table.lower() in q)
            score += sum(1 for c in columns if c.lower() in q)
            if score > best_score:
                best_score = score
                best = fq
        if best:
            return best

        return sorted(allowlist.keys())[0]

    def _pick_col(self, docs: List[Dict[str, Any]], allowed: Set[str], semantic_type: str) -> str | None:
        for d in docs:
            if d.get("semantic_type") == semantic_type and d.get("column_name") in allowed:
                return d["column_name"]
        return None

    def _build_sql(
        self,
        db_name: str,
        table_name: str,
        intent: Dict[str, Any],
        allowed_cols: Set[str],
        time_col: str | None,
        measure_col: str | None,
        dimension_col: str | None,
    ) -> str:
        metric = intent.get("metric", "count")
        time_range = intent.get("time_range", {})
        analysis_type = intent.get("analysis_type", "summary")

        metric_expr = "COUNT(*)"
        if metric == "sum" and measure_col:
            metric_expr = f"SUM(`{measure_col}`)"
        elif metric == "count_distinct":
            chosen = dimension_col or measure_col
            if chosen and chosen in allowed_cols:
                metric_expr = f"COUNT(DISTINCT `{chosen}`)"

        where_clauses = []
        if time_col and time_col in allowed_cols and time_range.get("kind") == "relative":
            value = int(time_range["value"])
            unit = str(time_range["unit"])
            unit_sql = "MONTH"
            if unit.startswith("day"):
                unit_sql = "DAY"
            elif unit.startswith("week"):
                unit_sql = "WEEK"
            elif unit.startswith("year"):
                unit_sql = "YEAR"
            where_clauses.append(f"`{time_col}` >= DATE_SUB(CURRENT_DATE, INTERVAL {value} {unit_sql})")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        if analysis_type == "trend" and time_col and time_col in allowed_cols:
            return (
                "SELECT DATE_FORMAT(`{time_col}`, '%Y-%m') AS period, {metric_expr} AS metric_value "
                "FROM `{db_name}`.`{table_name}` {where_sql} "
                "GROUP BY DATE_FORMAT(`{time_col}`, '%Y-%m') ORDER BY period"
            ).format(
                time_col=time_col,
                metric_expr=metric_expr,
                db_name=db_name,
                table_name=table_name,
                where_sql=where_sql,
            )

        return (
            "SELECT {metric_expr} AS metric_value "
            "FROM `{db_name}`.`{table_name}` {where_sql}"
        ).format(metric_expr=metric_expr, db_name=db_name, table_name=table_name, where_sql=where_sql)
