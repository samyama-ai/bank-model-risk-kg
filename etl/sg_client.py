"""Tiny HTTP client for a running Samyama server.

Talks to the server `cargo build --release` produces over its HTTP API
(POST /api/query, POST/GET /api/snapshot/*, GET /api/status). Keeping the
loader on plain HTTP means the only Python dependency is `requests` — no
wheel-build step for the Rust SDK.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class QueryResult:
    columns: list[str]
    records: list[list[Any]]
    elapsed_ms: float

    @property
    def rows(self) -> int:
        return len(self.records)

    def scalar(self) -> Any:
        if self.records and self.records[0]:
            return self.records[0][0]
        return None


class SamyamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8080", graph: str = "default"):
        self.base_url = base_url.rstrip("/")
        self.graph = graph

    def status(self) -> dict:
        r = requests.get(f"{self.base_url}/api/status", timeout=30)
        r.raise_for_status()
        return r.json()

    def node_count(self) -> int:
        return int(self.status().get("storage", {}).get("nodes", 0))

    def edge_count(self) -> int:
        return int(self.status().get("storage", {}).get("edges", 0))

    def query(self, cypher: str, graph: str | None = None) -> QueryResult:
        t0 = time.perf_counter()
        r = requests.post(
            f"{self.base_url}/api/query",
            json={"query": cypher, "graph": graph or self.graph},
            timeout=300,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if r.status_code != 200:
            try:
                msg = r.json().get("error", r.text)
            except Exception:
                msg = r.text
            raise RuntimeError(f"query failed ({r.status_code}): {msg}")
        body = r.json()
        return QueryResult(
            columns=body.get("columns", []),
            records=body.get("records", []),
            elapsed_ms=elapsed_ms,
        )

    def export_snapshot(self, path: str) -> None:
        r = requests.post(f"{self.base_url}/api/snapshot/export", timeout=3600)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)

    def create_vector_index(self, label: str, property_key: str,
                            dimensions: int, metric: str = "cosine") -> dict:
        """Create an HNSW vector index. Must be done BEFORE setting embeddings —
        on this build, an index created after insert does not backfill."""
        r = requests.post(
            f"{self.base_url}/api/vector/indexes",
            json={"label": label, "property_key": property_key,
                  "dimensions": dimensions, "metric": metric},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()

    def vector_search(self, label: str, property_key: str,
                      query_vector: list[float], k: int = 10) -> list[dict]:
        r = requests.post(
            f"{self.base_url}/api/vector-search",
            json={"label": label, "property_key": property_key,
                  "query_vector": query_vector, "k": k, "graph": self.graph},
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get("results", [])
