from typing import List

import httpx


class EmbeddingServiceClient:

    def __init__(self, base_url: str, timeout: float = 120.0, batch_size: int = 64):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)
        # A large document (e.g. up to 200MB) can chunk into thousands of
        # pieces. Embedding them all in one HTTP call risked either the
        # request timing out (the whole model run had to finish inside one
        # `timeout` window) or the JSON payload itself becoming huge. Batching
        # keeps each call small and bounded regardless of document size.
        self._batch_size = batch_size

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i:i + self._batch_size]
            r = self._client.post("/embed/documents", json={"texts": batch})
            r.raise_for_status()
            vectors.extend(r.json()["vectors"])
        return vectors
