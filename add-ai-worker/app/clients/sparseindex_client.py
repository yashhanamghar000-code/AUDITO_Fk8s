from typing import Any, Dict, List

import httpx


class SparseIndexServiceClient:

    def __init__(self, base_url: str, timeout: float = 60.0):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)

    def add_documents(self, user_id: str, chunks: List[Dict[str, Any]]) -> None:
        r = self._client.post("/documents", json={"user_id": user_id, "chunks": chunks})
        r.raise_for_status()
