from __future__ import annotations

from statistics import mean, pstdev
from typing import Any, Dict, List


def generate_insight(question: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "executive_summary": "No rows matched the query criteria.",
            "key_insights": ["The current filters produced an empty result set."],
            "recommendations": ["Broaden the time range or remove restrictive filters."],
            "limitations": "Insufficient data returned from source query.",
        }

    if "period" in rows[0] and "metric_value" in rows[0]:
        return _trend_insights(rows)

    metric_values = [r.get("metric_value") for r in rows if isinstance(r.get("metric_value"), (int, float))]
    if metric_values:
        val = metric_values[0]
        return {
            "executive_summary": f"Current metric value is {val:,.2f}.",
            "key_insights": [f"Answer generated for question: {question}"],
            "recommendations": ["Track this metric over time to add trend context."],
            "limitations": "Single aggregated value; no temporal pattern available.",
        }

    return {
        "executive_summary": "Result set returned non-numeric output.",
        "key_insights": ["Unable to derive quantitative trend from current result format."],
        "recommendations": ["Run a time-series aggregate query for deeper insight."],
        "limitations": "Metric value column missing or non-numeric.",
    }


def _trend_insights(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    clean_rows = [r for r in rows if isinstance(r.get("metric_value"), (int, float))]
    if len(clean_rows) < 2:
        return {
            "executive_summary": "Trend analysis needs at least two periods.",
            "key_insights": ["Only one data period was available."],
            "recommendations": ["Expand the lookback window to compare periods."],
            "limitations": "Insufficient period count for trend calculations.",
        }

    first = float(clean_rows[0]["metric_value"])
    last = float(clean_rows[-1]["metric_value"])
    change = last - first
    pct_change = (change / first * 100.0) if first != 0 else None

    values = [float(r["metric_value"]) for r in clean_rows]
    mu = mean(values)
    sigma = pstdev(values) if len(values) > 1 else 0.0

    anomalies = []
    if sigma > 0:
        for r in clean_rows:
            z = (float(r["metric_value"]) - mu) / sigma
            if abs(z) >= 2.0:
                anomalies.append((r["period"], float(r["metric_value"])))

    direction = "increased" if change >= 0 else "decreased"
    if pct_change is None:
        summary = f"Metric {direction} from {first:,.2f} to {last:,.2f}."
    else:
        summary = f"Metric {direction} by {abs(pct_change):.1f}% over the selected period."

    insights = [
        f"Start period value: {first:,.2f}; end period value: {last:,.2f}.",
        f"Absolute change: {change:,.2f}.",
    ]

    if anomalies:
        formatted = ", ".join([f"{p} ({v:,.2f})" for p, v in anomalies[:3]])
        insights.append(f"Potential anomalies detected at: {formatted}.")
    else:
        insights.append("No statistical anomalies detected at z-score threshold 2.0.")

    recommendations = []
    if change < 0:
        recommendations.append("Investigate recent operational or pricing changes that may be suppressing performance.")
        recommendations.append("Prioritize recovery actions on the most recent down periods.")
    else:
        recommendations.append("Sustain growth drivers and verify capacity planning for continued demand.")
        recommendations.append("Test targeted investments in channels with strongest recent lift.")

    return {
        "executive_summary": summary,
        "key_insights": insights,
        "recommendations": recommendations,
        "limitations": None,
    }
