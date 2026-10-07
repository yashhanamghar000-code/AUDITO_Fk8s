# Solo Audito backend analysis

Inspected repository: `Downloads/legal(1)/AUDITO`. Existing tracked files were clean before work. This report precedes Flutter implementation; existing services remain unchanged.

## Architecture and deployment

`add-ai-frontend` is a React/TypeScript Vite and TanStack web client. `add-ai-backend` is the public FastAPI facade, composed through `app/container.py`. `add-ai-auth-service` handles bcrypt passwords and JWTs; `add-ai-data-service` owns PostgreSQL persistence. `add-ai-core` defines shared Python entities/interfaces. Parsing, embeddings, reranking, LLM, vectorstore (Qdrant), and sparse-index services remain server-side. Celery workers ingest documents through Redis, with shared original-file storage. `audio-feature` holds web speech hooks. `add-ai-orchestration` contains additional deployment configuration.

Root Docker Compose wires the services and Kong (`add-ai-gateway/kong.yml`), publishing the gateway on port 80. Kong preserves `/api` when forwarding to backend:8000; other paths go to frontend:3000. Some data-store ports are also published. Kubernetes manifests in `k8s/` instead route ingress host `auditoai.online` directly to backend for `/api` and frontend for `/`. Jenkins files describe deployment automation. No mobile client should contact internal microservices.

## Discovered public API contracts

Paths below are literal router paths from `add-ai-backend/app/api/routers/` (all protected except auth login/register/logout and health).

| Method | Path | Request / result |
| --- | --- | --- |
| POST | `/api/auth/register` | JSON name, email, password → token and user {id,name,email} |
| POST | `/api/auth/login` | JSON email, password → same token/user envelope |
| GET | `/api/auth/me` | Bearer token → {id,name,email} |
| POST | `/api/auth/logout` | Returns status ok; no server token revocation |
| GET | `/api/health` | Health check |
| GET | `/api/conversations` | {conversations:[{session_id,title,created_at,updated_at}]} |
| GET | `/api/conversations/{session_id}/files` | {files:[{id,name,status,total_chunks_indexed,created_at}]} |
| GET | `/api/chat/history/{user_id}/{session_id}` | {history:[{sender:user or bot,text}]} with ownership check |
| POST | `/api/chat` | Multipart query, session_id, optional comma-separated file_ids → response, citations, sub_queries_used, follow_up_questions |
| POST | `/api/upload` | Multipart session_id and file → status queued, task_id, file_id |
| GET | `/api/upload/status/{task_id}` | state PENDING/PARSING/EMBEDDING/SUCCESS/FAILURE and optional detail/result |
| DELETE | `/api/documents/{file_id}` | Deletes owned file and indexed data |
| GET | `/api/documents/{file_id}/file` | Authenticated original PDF response |
| DELETE | `/api/session/{session_id}` | Clears session and associated data |
| POST | `/api/summarize` | Multipart file_id → summary |

Chat citations include source, page, file_id and optional snippet, bbox, page_width, page_height (see `add-ai-core/add_ai_core/entities/chat.py`). History persists text only, so historical citations cannot be reconstructed from that endpoint. Chat requires indexed files in the same session; a new empty session gets 404 until ingestion completes. Session IDs are client-generated; there is no create-conversation endpoint.

## Authentication and current web flow

`src/services/api.ts` creates Axios using VITE_API_BASE_URL, defaulting to http://localhost:8000, and attaches a sessionStorage bearer token. `auth.ts` calls the four public auth routes. The frontend Dockerfile defaults its build-time base URL to `/`, so deployed calls use the same origin. Chat/upload services submit FormData, retrieve conversations/history, and poll ingestion tasks.

The backend proxies auth to internal auth-service:8008. JWT verification on protected requests calls `/verify`; default JWT lifetime is 1440 minutes. There is no refresh-token API. Flutter should store the returned token in platform secure storage, restore by calling `/api/auth/me`, and clear the session on a protected 401. A transport/server error during restoration must offer retry without discarding the token. Logout must remove local credentials even if the server is unavailable.

## Configuration

Use API_BASE_URL as an origin, WITHOUT `/api`: source manifests indicate https://auditoai.online in production, http://localhost for root Compose, http://localhost:8000 for a separately exposed backend, and http://10.0.2.2 for Android emulator access to host Compose. Production reachability has not been tested. Endpoint constants own the `/api` prefix.

Environment files exist per service, under `env/`, and under orchestration. Inspected variable names without copying secret values: *_SERVICE_URL, REDIS_URL, DATABASE_URL, JWT_SECRET_KEY/JWT_ALGORITHM/JWT_EXPIRE_MINUTES, storage and retrieval limits, QDRANT_* settings, EMBEDDING_MODEL, RERANKER_MODEL, MISTRAL_* settings, mail configuration and API keys. These remain backend-only. Only the public origin belongs in Flutter dart-defines. CORS currently allows all origins in backend main.py; browser preview must use a reachable origin, and HTTPS pages cannot call an HTTP API.

## Missing APIs and integration limitations

No password recovery, refresh tokens, profile editing, notification feed, streaming chat, global document listing, or explicit conversation creation endpoint was found. Do not invent them. Documents are listed per session. Upload status verifies authentication but does not visibly check task ownership; document phase should resolve that server-side before relying on task IDs as private resources. Logout does not revoke JWTs. Retries of chat POST may duplicate persisted turns after ambiguous timeouts, so do not retry automatically. Full upload/progress/PDF viewing/history are deferred beyond phase one.

## Recommended Flutter architecture and phase one

Flutter UI → Riverpod controllers → domain repositories → API services → Dio → existing public backend → Auth/RAG/Documents/LLM. Keep endpoint constants/config, secure storage, themes, routing and error translation in core. Feature modules own auth, home and initial chat. Protected routes follow verified session state. Theme preferences are non-sensitive shared preferences. Use Android/iOS/web Flutter CLI targets and responsive Material 3 layouts. Implement functional auth and initial chat through discovered contracts; clearly mark document/history expansion as future work and never display fake account data or invented conversations. Add streaming behind the chat repository when a server contract exists.
