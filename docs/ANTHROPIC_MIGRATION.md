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

## Verified status (local, 2026-11-12; NOT deployed)
- **Gemini removal:** no tracked file references any other provider (only a binary favicon false positive). Built images contain `anthropic 2.8.0` and no google / genai / openai packages.
- **Tests:** llm-service 22 passed; backend 40 passed; `compileall` clean; `docker compose config` valid; images build; frontend `npm ci` and `npm run build` succeed. `npm run lint` reports ~7,500 prettier errors, nearly all CRLF line endings from the Windows checkout, plus 2 non-formatting lines; it is not a regression from this migration.
- **Key:** the running llm-service key matches the secure key file; a safe API call (models list and a one-word completion) succeeded; `claude-opus-5-5` is supported. The key is absent from tracked files, git history, image config and logs.

## Evaluation (20 cases, claude-opus-5-5, 2 synthetic users, 7 PDFs; original output kept in `results_ORIGINAL_claude_pass.json`)
| Metric | Result |
|---|---|
| Cases completed | 20 / 20 (HTTP 200 on all) |
| Correct (as originally scored) | 19 / 20 |
| Correct (after checker fixes) | 20 / 20 |
| Citation page check passed | 18 / 20 (Q09, Q09b flagged) |
| Fabricated references (original checker) | 27 flagged, all false positives (the regex captured the "- " bullet prefix) |
| Fabricated references (fixed checker, 108 references) | 0 |
| Average latency | 22.6 s (range 6.4-31 s; early cases inflated by a duplicate run) |
| Cost for 20 cases | about USD 1.21 |

Failures investigated:
- **Q14a (cross-user isolation):** original "fail" was a checker miss. The answer said "None of the retrieved passages mention Project Nightingale", which the not-found pattern did not match. No leakage of user B data (forbidden-hit list empty). Isolation held in Q14a and Q14c.
- **Q09 / Q09b:** answers correctly said the information was absent. The harness required zero citations for not-found questions. Q09 cited the FY2024 dividend and attributed it correctly to FY2024. Q09b cited the CEO's name page. These are strict-harness flags, not wrong answers.
- **Judge "unsupported" claims on Q11a/Q11b (long handbook):** the judge's fact sheet lacked the planted facts, so it flagged correct answers. Both cited the right pages (38 and 27). Treated as a judge artifact.
- **Q09b:** one mild genuine point: the answer attributed the March 2022 appointment date to the FY2024 page 1 instead of FY2025.
- The harness's optional comparison pass against the old backend returned 502 for all cases (the old provider is retired) and is irrelevant to the migration.
