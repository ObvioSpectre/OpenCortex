from __future__ import annotations

import re
from typing import Any, Dict


def extract_intent(question: str) -> Dict[str, Any]:
    q = question.lower()
    analysis_type = "trend" if any(k in q for k in ["trend", "over time", "growth", "decline"]) else "summary"

    metric = "count"
    if any(k in q for k in ["revenue", "sales", "amount", "gmv"]):
        metric = "sum"
    if any(k in q for k in ["distinct", "unique"]):
        metric = "count_distinct"

    time_range = _extract_time_range(q)
    compare_period = any(k in q for k in ["compare", "vs", "versus", "change", "last period", "previous"])

    return {
        "analysis_type": analysis_type,
        "metric": metric,
        "time_range": time_range,
        "compare_period": compare_period,
    }


def _extract_time_range(question_lower: str) -> Dict[str, Any]:
    m = re.search(r"last\s+(\d+)\s+(day|days|week|weeks|month|months|year|years)", question_lower)
    if not m:
        return {"kind": "default", "value": None, "unit": None}
    return {"kind": "relative", "value": int(m.group(1)), "unit": m.group(2)}
