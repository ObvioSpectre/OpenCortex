from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    payload: dict[str, Any]


class VectorStore(Protocol):
    def upsert(self, collection: str, records: list[VectorRecord]) -> None:
        ...

    def query(self, collection: str, vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        ...
