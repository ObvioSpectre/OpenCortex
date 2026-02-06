from __future__ import annotations

from typing import Any

from backend.vector.base import VectorRecord


class QdrantVectorStore:
    def __init__(self, url: str, api_key: str = "") -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import PointStruct, VectorParams, Distance
        except ImportError as exc:
            raise RuntimeError("qdrant-client is required for QdrantVectorStore") from exc

        self._qdrant_client_cls = QdrantClient
        self._point_cls = PointStruct
        self._vector_params_cls = VectorParams
        self._distance_cls = Distance
        self.client = QdrantClient(url=url, api_key=api_key or None)

    def upsert(self, collection: str, records: list[VectorRecord]) -> None:
        if not records:
            return
        size = len(records[0].vector)
        if not self.client.collection_exists(collection):
            self.client.recreate_collection(
                collection_name=collection,
                vectors_config=self._vector_params_cls(size=size, distance=self._distance_cls.COSINE),
            )

        points = [self._point_cls(id=r.id, vector=r.vector, payload=r.payload) for r in records]
        self.client.upsert(collection_name=collection, points=points)

    def query(self, collection: str, vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        if not self.client.collection_exists(collection):
            return []
        results = self.client.search(collection_name=collection, query_vector=vector, limit=top_k)
        return [r.payload for r in results]
