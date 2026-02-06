from backend.agent.pipeline import QueryPipeline
from backend.agent.sql_generator import SQLGenerator
from backend.vector.memory_store import InMemoryVectorStore
from backend.vector.service import VectorIndexService


def test_vector_search_filters_by_role():
    store = InMemoryVectorStore()
    service = VectorIndexService(store=store)

    docs = [
        {"id": "m1", "kind": "metric", "text": "revenue metric", "allowed_roles": ["finance", "admin"]},
        {"id": "m2", "kind": "metric", "text": "units sold metric", "allowed_roles": ["sales", "executive", "admin"]},
        {"id": "m3", "kind": "column", "text": "order date", "allowed_roles": []},
    ]
    service.index_documents("c1", docs)

    finance_docs = service.search("c1", "metric", top_k=10, role="finance")
    finance_ids = {d["id"] for d in finance_docs}
    assert "m1" in finance_ids
    assert "m2" not in finance_ids
    assert "m3" in finance_ids


def test_access_denied_response_message():
    store = InMemoryVectorStore()
    vector_index = VectorIndexService(store=store)
    pipeline = QueryPipeline(vector_index=vector_index, sql_generator=SQLGenerator())

    response = pipeline._access_denied_response(
        question="show revenue",
        organization_id="org_demo",
        user_id="alice",
        role="sales",
        data_source_id="default_mysql",
        denial_reason="restricted",
    )
    assert response["insight"]["executive_summary"] == "I can't provide that data right now."
    assert response["rows"] == []
