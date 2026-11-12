
from typing import Any, Dict, List, TypedDict

import httpx
from add_ai_core.exceptions import IngestionError


class ChunkDict(TypedDict):
    content: str
    metadata: Dict[str, Any]


class ParsingServiceClient:

    def __init__(self, base_url: str, timeout: float = 1200.0):
        
        timeout_config = httpx.Timeout(
            timeout=timeout,
            connect=15.0,   # 15s to establish connection
            read=timeout,   # 1200s (was 600s) — a large, OCR-heavy document
                            # up to 200MB can legitimately take longer than
                            # 10 minutes to parse page-by-page
        )
        self._client = httpx.Client(base_url=base_url, timeout=timeout_config)

    def parse(
        self,
        file_path: str,
        file_name: str,
        user_id: str,
        session_id: str,
        file_id: str,
    ) -> List[ChunkDict]:
        try:
            with open(file_path, "rb") as f:
                r = self._client.post(
                    "/parse",
                    files={"file": (file_name, f)},
                    data={
                        "user_id": user_id,
                        "session_id": session_id,
                        "file_id": file_id,
                    },
                )

            if r.status_code == 415:
                raise IngestionError(
                    r.json().get("detail", "Unsupported file type")
                )

            r.raise_for_status()
            return r.json()["chunks"]

        except httpx.ReadTimeout as e:
            raise IngestionError(
                f"Parsing service timed out processing '{file_name}' after "
                f"{self._client.timeout.read} seconds."
            ) from e
        except httpx.HTTPError as e:
            raise IngestionError(
                f"HTTP error occurred while contacting parsing service: {e}"
            ) from e