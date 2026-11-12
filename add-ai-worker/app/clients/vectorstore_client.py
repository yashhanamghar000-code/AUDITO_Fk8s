from typing import Any, Dict, List

import httpx


class VectorStoreServiceClient:

    def __init__(self, base_url: str, timeout: float = 120.0, batch_size: int = 200):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)
        # Same reasoning as EmbeddingServiceClient: a large document can
        # produce thousands of (chunk, vector) pairs, and sending them all
        # as one JSON body risked a very large request / timeout. Batching
        # keeps every call small no matter how big the source document was.
        self._batch_size = batch_size

    def upsert(self, chunks: List[Dict[str, Any]], vectors: List[List[float]], user_id: str, session_id: str) -> None:
        for i in range(0, len(chunks), self._batch_size):
            r = self._client.post("/upsert", json={
                "chunks": chunks[i:i + self._batch_size],
                "vectors": vectors[i:i + self._batch_size],
                "user_id": user_id,
                "session_id": session_id,
            })
            r.raise_for_status()
