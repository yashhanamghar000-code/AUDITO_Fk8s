# AUDITO: Anthropic Claude as the only LLM provider

AUDITO uses **Anthropic Claude exclusively**. There is no other provider in the code, images, environment files or documentation.

## What it consists of
| Area | File | Notes |
|---|---|---|
| LLM service | `add-ai-llm-service/app/client.py`, `app/main.py` | `AnthropicLlmClient` (official `anthropic` SDK, pinned `anthropic==2.8.0`). `POST /complete` keeps `{"text"}` and adds `provider, model, stop_reason, usage, request_id, latency_ms`. |
| Errors | same | Provider errors map to 429 / 503 / 504 / 502 / 422 with user-safe messages; no keys or request content in responses or logs. |
| System prompt | `add-ai-backend/app/prompts/audito_system_prompt.py` | Owner prompt (sections A-G) verbatim + runtime protocol (H-I). |
| RAG workflow | `add-ai-backend/app/services/chat_workflow_service.py` | `[SOURCE n \| File \| Page]` labels, conversation history sent to the model and to query rewriting, citations built only from sources the model reports using (validated against retrieval). |
| Router | `add-ai-backend/app/api/routers/chat_router.py` | Loads this user's history for the session; LLM errors mapped to safe HTTP errors; no internal exception text returned. |

## Configuration (llm-service, environment variables)
`ANTHROPIC_API_KEY` (secret, required), `ANTHROPIC_MODEL` (default `claude-opus-5-5`), `ANTHROPIC_EFFORT` (`low|medium|high|xhigh|max`, default `medium`),
`ANTHROPIC_MAX_TOKENS` (16000), `ANTHROPIC_TIMEOUT_SECONDS` (120), `ANTHROPIC_MAX_RETRIES` (2), `ANTHROPIC_REFUSAL_FALLBACK` (true).
Backend: `CHAT_HISTORY_MESSAGES` (default 6).
Secrets live only in `env/*.env` on the server (chmod 600, gitignored) - never in images, build args or Git.
`claude-opus-5-5` takes no `temperature`/`top_p`; thinking is adaptive and always on, so depth is set with `ANTHROPIC_EFFORT`.
A cheaper model (for example `claude-sonnet-5-5`) can be selected by changing `ANTHROPIC_MODEL` only.

## Rollback (previous production version)
Before each deployment, tag the running images (`docker tag harshpaygude/audito-<svc>:latest audito-<svc>:rollback-<date>`) and back up `env/` and `docker-compose.yml`.
To roll back: `docker tag audito-<svc>:rollback-<date> harshpaygude/audito-<svc>:latest`, restore the env files from the backup, then
`docker compose up -d --no-deps --force-recreate llm-service backend`.
NEVER run `docker compose pull` on the server (it replaces locally built images with older registry images).

## Deployment runbook (requires owner approval before it is run)
1. Back up `~/recovery/<date>/` (env files, compose, `pg_dump`) and tag current images `rollback-<date>`.
2. Copy the changed source (`add-ai-llm-service`, `add-ai-backend`) to `~/AUDITO/AUDITO`.
3. In `env/llm-service.env` set `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` through a protected channel (never echoed) and remove every old-provider variable.
4. `docker compose build llm-service backend`, then `up -d --no-deps --force-recreate llm-service backend`.
5. Smoke-test through https://auditoai.online (register, upload, chat, citations) and watch `docker compose logs llm-service` for `provider=anthropic`.
