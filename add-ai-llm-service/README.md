# add-ai-llm-service

Thin HTTP wrapper around the Anthropic Claude Messages API (official `anthropic` SDK).
Implements `ILLMClient` from `add-ai-core`. All prompt engineering stays in the caller
(`add-ai-backend`'s `chat_workflow_service` and `app/prompts/`) - this service only knows
how to talk to Claude. Claude is AUDITO's only LLM provider.

## API
POST `/complete` - `{"messages": [{"role": "system"|"user"|"assistant", "content": "..."}], "max_tokens": 600?, "effort": "low"?}`
-> `{"text": "...", "provider": "anthropic", "model": "...", "stop_reason": "...", "usage": {...}, "request_id": "...", "latency_ms": 0}`

Errors are returned with user-safe messages: 429 (rate limited, with `Retry-After`), 503 (overloaded/unreachable),
504 (timeout), 422 (request declined), 502 (provider/credential problem), 400 (bad request).
API keys, prompts and answers are never logged or returned - only token counts, latency and request ids.

## Configuration
See `.env.example`: `ANTHROPIC_API_KEY` (required, secret), `ANTHROPIC_MODEL` (default `claude-opus-5-5`),
`ANTHROPIC_EFFORT`, `ANTHROPIC_MAX_TOKENS`, `ANTHROPIC_TIMEOUT_SECONDS`, `ANTHROPIC_MAX_RETRIES`, `ANTHROPIC_REFUSAL_FALLBACK`.

## Run standalone
```bash
cp .env.example .env   # fill in ANTHROPIC_API_KEY (never commit it)
docker compose up --build
curl -X POST localhost:8003/complete -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"say hi"}]}'
```

## Tests
```bash
pip install -r requirements.txt pytest httpx && pip install -e ../add-ai-core
PYTHONPATH=. pytest tests
```
