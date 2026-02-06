from __future__ import annotations

from backend.agent.pipeline import QueryPipeline
from backend.agent.sql_generator import SQLGenerator
from backend.vector.service import VectorIndexService, get_vector_store

vector_store = get_vector_store()
vector_index_service = VectorIndexService(store=vector_store)
query_pipeline = QueryPipeline(vector_index=vector_index_service, sql_generator=SQLGenerator())
