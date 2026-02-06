from __future__ import annotations

import hashlib
from typing import Any, Iterable

import requests

from backend.config import settings
from backend.vector.base import VectorRecord, VectorStore


def get_vector_store() -> VectorStore:
    if settings.vector_provider == "qdrant" and settings.qdrant_url:
        from backend.vector.qdrant_store import QdrantVectorStore

        return QdrantVectorStore(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

    from backend.vector.memory_store import InMemoryVectorStore

    return InMemoryVectorStore()


class EmbeddingClient:
    def is_configured(self) -> bool:
        return bool(settings.llm_api_base and settings.llm_api_key)

    def embed(self, text: str) -> list[float]:
        if self.is_configured():
            try:
                response = requests.post(
                    f"{settings.llm_api_base.rstrip('/')}/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": settings.embedding_model, "input": text},
                    timeout=30,
                )
                response.raise_for_status()
                return response.json()["data"][0]["embedding"]
            except Exception:
                pass
        return self._deterministic_vector(text)

    def _deterministic_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [((b / 255.0) * 2.0) - 1.0 for b in digest]


class VectorIndexService:
    def __init__(self, store: VectorStore, embedder: EmbeddingClient | None = None) -> None:
        self.store = store
        self.embedder = embedder or EmbeddingClient()

    def index_documents(self, collection: str, docs: Iterable[dict[str, Any]]) -> int:
        records = []
        for doc in docs:
            text = doc.get("text", "")
            doc_id = doc.get("id")
            if not text or not doc_id:
                continue
            records.append(VectorRecord(id=doc_id, vector=self.embedder.embed(text), payload=doc))
        self.store.upsert(collection, records)
        return len(records)

    def search(self, collection: str, query: str, top_k: int = 5, role: str | None = None) -> list[dict[str, Any]]:
        vec = self.embedder.embed(query)
        candidates = self.store.query(collection, vec, top_k=max(top_k * 5, 25))
        filtered: list[dict[str, Any]] = []
        for doc in candidates:
            if role is None:
                filtered.append(doc)
                continue
            allowed_roles = doc.get("allowed_roles") or []
            if not allowed_roles or role in allowed_roles:
                filtered.append(doc)
        return filtered[:top_k]

    def build_semantic_docs(self, data_source_id: str, semantic_model: dict[str, Any]) -> list[dict[str, Any]]:
        docs = []
        for table in semantic_model.get("semantic_tables", []):
            doc_id = f"{data_source_id}:table:{table['database_name']}.{table['table_name']}"
            text = (
                f"Table {table['database_name']}.{table['table_name']} visible roles {table.get('allowed_roles', [])}. "
                f"Columns: {[c.get('column_name') for c in table.get('columns', [])]}"
            )
            docs.append({"id": doc_id, "kind": "table", "text": text, **table})

        for col in semantic_model.get("semantic_columns", []):
            doc_id = f"{data_source_id}:col:{col['database_name']}.{col['table_name']}.{col['column_name']}"
            text = (
                f"Table {col['database_name']}.{col['table_name']} column {col['column_name']} "
                f"is a {col['semantic_type']}. {col['description']} "
                f"Metrics: {col['metric_candidates']}. Allowed roles: {col.get('allowed_roles', [])}"
            )
            docs.append({"id": doc_id, "kind": "column", "text": text, **col})

        for metric in semantic_model.get("metrics", []):
            doc_id = f"{data_source_id}:metric:{metric['name']}"
            text = (
                f"Metric {metric['name']}: {metric['description']}. SQL: {metric['expression_sql']}. "
                f"Allowed roles: {metric.get('allowed_roles', [])}"
            )
            docs.append({"id": doc_id, "kind": "metric", "text": text, **metric})

        return docs
