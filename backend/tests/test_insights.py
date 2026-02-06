from backend.agent.insights import generate_insight


def test_trend_insight_increase():
    rows = [
        {"period": "2025-01", "metric_value": 100},
        {"period": "2025-02", "metric_value": 120},
        {"period": "2025-03", "metric_value": 150},
    ]
    insight = generate_insight("sales trend", rows)
    assert "increased" in insight["executive_summary"]
    assert len(insight["recommendations"]) >= 1


def test_empty_rows_limitation():
    insight = generate_insight("sales trend", [])
    assert insight["limitations"] is not None
