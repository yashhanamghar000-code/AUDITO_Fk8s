# AUDITO: Anthropic Claude provider and AUDITO system prompt

## What changed
| Area | File | Change |
|---|---|---|
| LLM provider | `add-ai-llm-service/app/client.py`, `app/main.py` | `LLM_PROVIDER=anthropic\|gemini`; `AnthropicLlmClient` (official `anthropic` SDK); Gemini client unchanged (rollback). `/complete` keeps `{"text"}` and adds `provider, model, stop_reason, usage, request_id, latency_ms`. |
| Errors | same | Provider errors -> 429 / 503 / 504 / 502 / 422 with user-safe messages; no keys or request content in responses or logs. |
| System prompt | `add-ai-backend/app/prompts/audito_system_prompt.py` | Owner prompt (sections A-G) verbatim + runtime protocol (H-I). `AUDITO_PROMPT=legacy` restores the previous prompt. |
| RAG workflow | `add-ai-backend/app/services/chat_workflow_service.py` | `[SOURCE n \| File \| Page]` labels, conversation history sent to the model and to query rewriting, citations built only from sources the model reports using (validated against retrieval). |
| Router | `add-ai-backend/app/api/routers/chat_router.py` | Loads this user's history for the session; LLM errors mapped to safe HTTP errors; no internal exception text returned. |

## Configuration (llm-service)
`LLM_PROVIDER`, `ANTHROPIC_API_KEY` (secret), `ANTHROPIC_MODEL`, `ANTHROPIC_EFFORT`, `ANTHROPIC_MAX_TOKENS`,
`ANTHROPIC_TIMEOUT_SECONDS`, `ANTHROPIC_MAX_RETRIES`, `ANTHROPIC_REFUSAL_FALLBACK`. Gemini variables are untouched.
Backend: `AUDITO_PROMPT` (audito|legacy), `CHAT_HISTORY_MESSAGES` (default 6).
Secrets live only in `env/*.env` on the server (chmod 600, gitignored) - never in images, build args or Git.

## Rollback (seconds, no rebuild)
1. `env/llm-service.env`: set `LLM_PROVIDER=gemini` (keep the Gemini key/model lines).
2. Optional: `env/backend.env`: `AUDITO_PROMPT=legacy`.
3. `docker compose up -d --no-deps --force-recreate llm-service backend`.
To restore the previous *images*: `docker tag audito-<svc>:rollback-<date> harshpaygude/audito-<svc>:latest` then recreate.

## Deployment runbook (NOT executed - requires owner approval)
1. Back up: `~/recovery/<date>/` (env files, compose, DB `pg_dump`), tag current images `rollback-<date>`.
2. Copy changed source (llm-service, backend) to `~/AUDITO/AUDITO`.
3. Append to `env/llm-service.env` (via a protected channel, never echoed): `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`.
4. `docker compose build llm-service backend` -> `up -d --no-deps --force-recreate llm-service backend`.
5. Smoke-test through https://auditoai.online (register, upload, chat, citations), watch `docker compose logs llm-service` for `provider=anthropic`.
NEVER run `docker compose pull` on the server (it replaces locally built images with older registry images).
