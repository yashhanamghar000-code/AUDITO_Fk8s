# add-ai-orchestration

The one repo that knows every other repo exists. Wires all 12 runtime
repos (11 services + the frontend) together with `docker-compose.yml`,
using pre-built images only — this repo never builds anything itself,
per the platform convention of "each repo builds its own image."

## Checkout layout

Clone every repo as a sibling of this one:

```
workspace/
├── add-ai-orchestration/     (this repo)
├── add-ai-core/               (shared library, no image)
├── add-ai-frontend/
├── add-ai-backend/
├── add-ai-worker/
├── add-ai-auth-service/
├── add-ai-data-service/
├── add-ai-embeddings-service/
├── add-ai-reranker-service/
├── add-ai-llm-service/
├── add-ai-vectorstore-service/
├── add-ai-sparseindex-service/
└── add-ai-parsing-service/
```

## Run the whole platform

```bash
./build-all.sh          # or: make build
docker compose up       # or: make up
```

Then:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Every other service's port is listed in `docker-compose.yml`'s
  comments — reachable from your host too, for poking at one service
  directly with `curl` while the rest of the stack is up.

Fill in real secrets first — copy each `env/*.env` file's placeholders
(`MY_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `JWT_SECRET_KEY`) with real
values before `docker compose up`.

## Local development across multiple repos at once

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

This layers a live-reload override on top of every service: each one's
source is bind-mounted from its sibling repo, `add-ai-core` is
`pip install -e`'d fresh on every container start, and every Python
service runs with `--reload`. Edit a file in any repo and that one
service picks it up — no rebuild.

If you're only touching ONE repo, it's usually faster to `cd` into that
repo and use **its own** `docker-compose.yml` (every repo has one) to
test it completely standalone, pointed at either mocked/local
dependencies or at the shared stack you already have running here via
its published port. See that repo's own README.

## Common tasks

| Task | Command |
|---|---|
| Start everything | `make up` |
| Start everything, detached | `make up-d` |
| Tail all logs | `make logs` |
| Restart just the worker after a worker-repo change | `make restart-worker` |
| Scale ingestion to 3 parallel workers | `make scale-worker` |
| Stop everything | `make down` |
| Stop AND wipe all data (Postgres/Qdrant/BM25/uploads) | `make clean` |

## Why this design

Each of the 11 backend repos does exactly one job and is independently:
- **buildable** — its own `Dockerfile`, no shared build context
- **runnable** — its own `docker-compose.yml` brings up just enough
  (a database, a queue, or nothing) to exercise it alone
- **swappable** — every adapter it wraps implements an interface from
  `add-ai-core`; a new implementation only needs a new class + a new
  image, never a change to any caller

The trade-off, made explicit rather than hidden: every call between
services is now a network hop instead of a Python function call, and
there are more moving parts to keep running locally. `docker-compose.dev.yml`
and each repo's own compose files exist specifically to keep that
trade-off from making local development painful.

## Where things live (migration map from the original monorepo)

| Original path | New repo |
|---|---|
| `backend/app/core/` | `add-ai-core` |
| `backend/app/infrastructure/embeddings/` | `add-ai-embeddings-service` |
| `backend/app/infrastructure/reranking/` | `add-ai-reranker-service` |
| `backend/app/infrastructure/llm/` | `add-ai-llm-service` |
| `backend/app/infrastructure/vector_store/` | `add-ai-vectorstore-service` |
| `backend/app/infrastructure/sparse_index/` | `add-ai-sparseindex-service` |
| `backend/app/infrastructure/parsing/` | `add-ai-parsing-service` |
| `backend/app/infrastructure/security/` | `add-ai-auth-service` |
| `backend/app/infrastructure/db/`, `repositories/` | `add-ai-data-service` |
| `backend/app/infrastructure/queue/`, ingestion orchestration | `add-ai-worker` |
| `backend/app/services/`, `api/`, `container.py`, `main.py` | `add-ai-backend` |
| `frontend/frontend_audito/` | `add-ai-frontend` |
| `docker-compose.yml` (root) | `add-ai-orchestration` (this repo) |
