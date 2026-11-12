import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from add_ai_core.interfaces.llm_client import ILLMClient

logger = logging.getLogger("audito.llm_client")


class LlmServiceError(Exception):
    """The llm-service failed. `status_code`/`detail` are already safe to show a user."""

    def __init__(self, status_code: int, detail: str, category: str = "llm_error"):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.category = category


class LlmServiceClient(ILLMClient):

    def __init__(self, base_url: str, timeout: float = 180.0):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)
        # Token usage of the most recent call on this thread-agnostic client is
        # intentionally not stored; callers that need it use complete_ex().

    def complete(
        self,
        messages: List[Tuple[str, str]],
        max_tokens: Optional[int] = None,
        effort: Optional[str] = None,
    ) -> str:
        return self.complete_ex(messages, max_tokens=max_tokens, effort=effort)["text"]

    def complete_ex(
        self,
        messages: List[Tuple[str, str]],
        max_tokens: Optional[int] = None,
        effort: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"messages": [{"role": role, "content": content} for role, content in messages]}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if effort:
            payload["effort"] = effort

        try:
            r = self._client.post("/complete", json=payload)
        except httpx.TimeoutException as exc:
            raise LlmServiceError(504, "The AI service took too long to respond. Please try again.", "timeout") from exc
        except httpx.HTTPError as exc:
            raise LlmServiceError(503, "The AI service is unreachable right now. Please try again.", "unreachable") from exc

        if r.status_code >= 400:
            detail, category = "The AI service returned an error.", "llm_error"
            try:
                body = r.json()
                detail = body.get("detail", detail) if isinstance(body, dict) else detail
                category = body.get("category", category) if isinstance(body, dict) else category
            except ValueError:
                pass
            # Only forward statuses a client can act on; collapse internal ones to 502/503.
            status = r.status_code if r.status_code in (400, 422, 429, 503, 504) else 502
            raise LlmServiceError(status, str(detail), str(category))

        body = r.json()
        usage = body.get("usage") or {}
        if usage:
            logger.info(
                "llm usage provider=%s model=%s in=%s out=%s cache_read=%s stop=%s latency_ms=%s",
                body.get("provider"), body.get("model"), usage.get("input_tokens"), usage.get("output_tokens"),
                usage.get("cache_read_input_tokens"), body.get("stop_reason"), body.get("latency_ms"),
            )
        return body
