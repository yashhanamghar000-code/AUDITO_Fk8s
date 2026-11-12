import httpx


class DataServiceClient:

    def __init__(self, base_url: str, timeout: float = 15.0):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)

    def update_file_status(self, file_id: int, status: str, total_chunks_indexed: int = 0) -> None:
        r = self._client.patch(f"/files/{file_id}/status", json={
            "status": status, "total_chunks_indexed": total_chunks_indexed,
        })
        r.raise_for_status()
