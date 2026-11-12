# add-ai-worker

The Celery consumer for async document ingestion. Listens on the same
Redis broker `add-ai-backend`'s `/api/upload` endpoint enqueues into, and
runs the actual parse → embed → upsert → index pipeline by calling
`add-ai-parsing-service`, `add-ai-embeddings-service`,
`add-ai-vectorstore-service`, `add-ai-sparseindex-service`, and
`add-ai-data-service` over HTTP.

## Why this is its own repo/image
Ingestion is CPU/GPU-bound and bursty (uploads happen unevenly) —
scaling it independently of the request-serving API (`add-ai-backend`)
with `docker compose up --scale worker=3` is the whole point of pulling
it out of the original monolith's combined `backend` + `worker` compose
services.

## Contract with add-ai-backend
Both repos must agree on:
- the Celery task name: `app.tasks.process_document_task`
- its positional args: `(file_path, file_name, user_id, session_id, file_id)`
- the Redis broker URL (`REDIS_URL`, same value in both `.env` files)
- the shared storage volume where uploaded files land (`STORAGE_DIR` in
  add-ai-backend, mounted here too — see `add-ai-orchestration`)

This is the one place in the platform where two repos share more than an
HTTP contract (a task name/signature, and a filesystem path convention)
— documented here and in `add-ai-backend`'s README since Celery doesn't
give you a schema to enforce it.

## Run standalone
Needs every downstream service reachable. The bundled compose file lists
them by image name — build or pull each sibling repo first:
```bash
cp .env.example .env
docker compose up --build
```

## Local dev
Live-reload isn't very meaningful for a Celery worker (no HTTP server to
reload), but `docker-compose.override.yml` still bind-mounts `./app` and
an editable `add-ai-core`, and restarts on `docker compose restart worker`
after a code change.

## Testing
`tests/test_ingestion_orchestrator.py` mocks every HTTP client so the
orchestration logic (what calls what, in what order) is unit-testable
with no network at all:
```bash
pip install -r requirements.txt pytest
pytest
```
