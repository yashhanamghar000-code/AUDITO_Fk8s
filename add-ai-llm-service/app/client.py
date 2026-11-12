"""LLM provider clients for the AUDITO llm-service.

Two interchangeable providers sit behind the same `complete`/`complete_ex`
interface, selected at start-up by LLM_PROVIDER (see app/main.py):

* GeminiLlmClient     - the original implementation (kept as the rollback path)
* AnthropicLlmClient  - Anthropic Claude through the official `anthropic` SDK

Security: API keys are only ever read from the environment by the caller and
passed to the SDK. They are never logged, returned in responses or included in
error messages. Prompts and completions are never logged - only metadata
(model, token counts, latency, stop reason, request id).
"""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from add_ai_core.interfaces.llm_client import ILLMClient

logger = logging.getLogger("audito.llm")


class LlmProviderError(Exception):
    """A provider failure translated into something safe to show callers.

    `status_code` is the HTTP status the llm-service answers with and
    `category` is a stable machine-readable label. `message` never contains
    credentials or request content.
    """

    def __init__(self, status_code: int, category: str, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.category = category
        self.message = message
        self.retry_after = retry_after


@dataclass
class LlmResult:
    text: str
    provider: str
    model: str
    stop_reason: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None
    latency_ms: Optional[int] = None


# --------------------------------------------------------------------------- #
# Gemini (original implementation, unchanged behaviour)
# --------------------------------------------------------------------------- #
class GeminiLlmClient(ILLMClient):

    def __init__(self, model: str, api_key: str, base_url: str, temperature: float = 0.1):
        # Imported lazily so an Anthropic-only deployment does not need the
        # LangChain/OpenAI stack to be importable at start-up.
        from langchain_openai import ChatOpenAI

        self._model = model
        self._llm = ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=temperature)

    def complete(self, messages: List[Tuple[str, str]]) -> str:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        lc_messages = []
        for role, content in messages:
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        return self._llm.invoke(lc_messages).content

    def complete_ex(
        self,
        messages: List[Tuple[str, str]],
        max_tokens: Optional[int] = None,
        effort: Optional[str] = None,
    ) -> LlmResult:
        started = time.monotonic()
        try:
            text = self.complete(messages)
        except Exception as exc:  # provider SDK errors differ; keep the message generic
            logger.error("gemini request failed: %s", type(exc).__name__)
            raise LlmProviderError(502, "provider_error", "The language model provider returned an error.") from exc
        latency = int((time.monotonic() - started) * 1000)
        logger.info("llm provider=gemini model=%s latency_ms=%d", self._model, latency)
        return LlmResult(text=text, provider="gemini", model=self._model, latency_ms=latency)


# --------------------------------------------------------------------------- #
# Anthropic Claude
# --------------------------------------------------------------------------- #
class AnthropicLlmClient(ILLMClient):
    """Claude via the official Anthropic SDK.

    Notes on the model family used here (claude-opus-5-5 / claude-sonnet-5-5):
    sampling parameters (temperature/top_p/top_k) are rejected with a 400, so
    none are sent; thinking is adaptive and always on, so `thinking` is omitted
    and depth is controlled with `output_config.effort` instead.
    """

    VALID_EFFORTS = {"low", "medium", "high", "xhigh", "max"}

    def __init__(
        self,
        model: str,
        api_key: str,
        max_tokens: int = 16000,
        effort: str = "medium",
        timeout_seconds: float = 120.0,
        max_retries: int = 2,
        refusal_fallback: bool = True,
    ):
        import anthropic  # imported lazily: the Gemini-only path must not require it

        self._anthropic = anthropic
        self._model = model
        self._max_tokens = max_tokens
        self._effort = effort if effort in self.VALID_EFFORTS else "medium"
        self._refusal_fallback = refusal_fallback
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds, max_retries=max_retries)

    # -- ILLMClient --------------------------------------------------------- #
    def complete(self, messages: List[Tuple[str, str]]) -> str:
        return self.complete_ex(messages).text

    # -- richer API used by the HTTP layer ---------------------------------- #
    def complete_ex(
        self,
        messages: List[Tuple[str, str]],
        max_tokens: Optional[int] = None,
        effort: Optional[str] = None,
    ) -> LlmResult:
        system_text, api_messages = self._to_api_messages(messages)
        if not api_messages:
            raise LlmProviderError(400, "invalid_request", "No user content was provided to the language model.")

        params: Dict[str, Any] = {
            "model": self._model,
            "max_tokens": int(max_tokens or self._max_tokens),
            "messages": api_messages,
            "output_config": {"effort": effort if effort in self.VALID_EFFORTS else self._effort},
        }
        if system_text:
            # The AUDITO system prompt is large and identical on every request,
            # so mark it cacheable (cheaper + faster on repeat turns).
            params["system"] = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]

        started = time.monotonic()
        try:
            if self._refusal_fallback:
                response = self._client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **params
                )
            else:
                response = self._client.messages.create(**params)
        except Exception as exc:
            raise self._translate_error(exc) from exc

        latency = int((time.monotonic() - started) * 1000)
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text").strip()
        usage = self._usage_dict(response)
        request_id = getattr(response, "_request_id", None)
        stop_reason = getattr(response, "stop_reason", None)

        logger.info(
            "llm provider=anthropic model=%s served_by=%s stop=%s in=%s out=%s cache_read=%s cache_write=%s latency_ms=%d request_id=%s",
            self._model,
            getattr(response, "model", self._model),
            stop_reason,
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            usage.get("cache_read_input_tokens"),
            usage.get("cache_creation_input_tokens"),
            latency,
            request_id,
        )

        if stop_reason == "refusal":
            raise LlmProviderError(
                422,
                "refused",
                "The language model declined to answer this request. Please rephrase your question.",
            )
        if not text:
            raise LlmProviderError(502, "empty_response", "The language model returned an empty response.")
        if stop_reason == "max_tokens":
            logger.warning("llm response truncated at max_tokens request_id=%s", request_id)

        return LlmResult(
            text=text,
            provider="anthropic",
            model=getattr(response, "model", self._model),
            stop_reason=stop_reason,
            usage=usage,
            request_id=request_id,
            latency_ms=latency,
        )

    # -- helpers ------------------------------------------------------------ #
    @staticmethod
    def _to_api_messages(messages: List[Tuple[str, str]]) -> Tuple[str, List[Dict[str, str]]]:
        system_parts: List[str] = []
        api_messages: List[Dict[str, str]] = []
        for role, content in messages:
            if not content or not str(content).strip():
                continue
            if role == "system":
                system_parts.append(content)
            else:
                api_messages.append({"role": "assistant" if role == "assistant" else "user", "content": content})
        # The Messages API requires the conversation to start with a user turn.
        while api_messages and api_messages[0]["role"] != "user":
            api_messages.pop(0)
        return "\n\n".join(system_parts), api_messages

    @staticmethod
    def _usage_dict(response: Any) -> Dict[str, Any]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return {}
        return {
            key: getattr(usage, key)
            for key in (
                "input_tokens",
                "output_tokens",
                "cache_creation_input_tokens",
                "cache_read_input_tokens",
            )
            if getattr(usage, key, None) is not None
        }

    def _translate_error(self, exc: Exception) -> LlmProviderError:
        a = self._anthropic
        request_id = getattr(exc, "request_id", None)
        if isinstance(exc, a.RateLimitError):
            retry_after = None
            try:
                retry_after = int(exc.response.headers.get("retry-after", "30"))
            except Exception:
                pass
            logger.warning("anthropic rate limited request_id=%s", request_id)
            return LlmProviderError(429, "rate_limited", "The AI service is busy right now. Please try again shortly.", retry_after)
        if isinstance(exc, a.APITimeoutError):
            logger.warning("anthropic timeout")
            return LlmProviderError(504, "timeout", "The AI service took too long to respond. Please try again.")
        if isinstance(exc, a.APIConnectionError):
            logger.error("anthropic connection error")
            return LlmProviderError(503, "connection_error", "Could not reach the AI service. Please try again.")
        if isinstance(exc, (a.AuthenticationError, a.PermissionDeniedError)):
            # Operator problem, not a user problem: log loudly, tell the caller nothing sensitive.
            logger.error("anthropic credentials rejected (%s) request_id=%s", type(exc).__name__, request_id)
            return LlmProviderError(502, "provider_auth", "The AI service is temporarily unavailable.")
        if isinstance(exc, a.NotFoundError):
            logger.error("anthropic model not found/available: %s request_id=%s", self._model, request_id)
            return LlmProviderError(502, "model_unavailable", "The AI service is temporarily unavailable.")
        if isinstance(exc, a.BadRequestError):
            logger.error("anthropic bad request request_id=%s", request_id)
            return LlmProviderError(400, "bad_request", "The request could not be processed by the AI service.")
        if isinstance(exc, a.APIStatusError):
            status = getattr(exc, "status_code", 500)
            logger.error("anthropic api error status=%s request_id=%s", status, request_id)
            if status in (500, 502, 503, 504, 529):
                return LlmProviderError(503, "overloaded", "The AI service is overloaded. Please try again shortly.")
            return LlmProviderError(502, "provider_error", "The AI service returned an error.")
        logger.exception("unexpected llm error")
        return LlmProviderError(500, "internal", "An unexpected error occurred while generating the answer.")
