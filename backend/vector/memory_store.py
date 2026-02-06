from __future__ import annotations

import math
from collections import defaultdict

from backend.vector.base import VectorRecord


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._collections: dict[str, list[VectorRecord]] = defaultdict(list)

    def upsert(self, collection: str, records: list[VectorRecord]) -> None:
        existing = {r.id: r for r in self._collections[collection]}
        for r in records:
            existing[r.id] = r
        self._collections[collection] = list(existing.values())

    def query(self, collection: str, vector: list[float], top_k: int = 5) -> list[dict]:
        rows = self._collections.get(collection, [])
        scored = []
        for rec in rows:
            score = _cosine_similarity(vector, rec.vector)
            scored.append((score, rec.payload))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:top_k]]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    a1, b1 = a[:n], b[:n]
    dot = sum(x * y for x, y in zip(a1, b1))
    na = math.sqrt(sum(x * x for x in a1))
    nb = math.sqrt(sum(y * y for y in b1))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
