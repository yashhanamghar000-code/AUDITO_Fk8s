import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.client import AnthropicLlmClient, GeminiLlmClient, LlmProviderError

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="add-ai-llm-service")


def build_client():
    """Select the LLM provider from LLM_PROVIDER (default: gemini, i.e. no behaviour change).

    Roll back from Claude to Gemini by setting LLM_PROVIDER=gemini and restarting
    only this service; the Gemini settings below are unchanged.
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    if provider == "anthropic":
        return AnthropicLlmClient(
            model=os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5"),
            api_key=os.environ["ANTHROPIC_API_KEY"],
            max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "16000")),
            effort=os.getenv("ANTHROPIC_EFFORT", "medium"),
            timeout_seconds=float(os.getenv("ANTHROPIC_TIMEOUT_SECONDS", "120")),
            max_retries=int(os.getenv("ANTHROPIC_MAX_RETRIES", "2")),
            refusal_fallback=os.getenv("ANTHROPIC_REFUSAL_FALLBACK", "true").lower() == "true",
        )
    if provider == "gemini":
        return GeminiLlmClient(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
            api_key=os.environ["GEMINI_API_KEY"],
            base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
        )
    raise RuntimeError(f"Unsupported LLM_PROVIDER '{provider}' (expected 'anthropic' or 'gemini')")


_client = build_client()


class Message(BaseModel):
    role: str
    content: str


class CompleteRequest(BaseModel):
    messages: List[Message]
    # Optional per-request tuning (ignored by providers that do not support it).
    max_tokens: Optional[int] = None
    effort: Optional[str] = None


class CompleteResponse(BaseModel):
    text: str
    # Additive metadata - older callers that only read `text` keep working.
    provider: Optional[str] = None
    model: Optional[str] = None
    stop_reason: Optional[str] = None
    usage: Dict[str, Any] = {}
    request_id: Optional[str] = None
    latency_ms: Optional[int] = None


@app.exception_handler(LlmProviderError)
async def provider_error_handler(_, exc: LlmProviderError):
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "category": exc.category},
        headers=headers,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/complete", response_model=CompleteResponse)
def complete(req: CompleteRequest):
    pairs: List[Tuple[str, str]] = [(m.role, m.content) for m in req.messages]
    result = _client.complete_ex(pairs, max_tokens=req.max_tokens, effort=req.effort)
    return CompleteResponse(
        text=result.text,
        provider=result.provider,
        model=result.model,
        stop_reason=result.stop_reason,
        usage=result.usage,
        request_id=result.request_id,
        latency_ms=result.latency_ms,
    )
