# add-ai-vectorstore-service

Dense-vector persistence + tenant-filtered similarity search on Qdrant.
Implements `IVectorStore` from `add-ai-core`.

## API
- `POST /upsert` — `{chunks, vectors, user_id, session_id}`
- `POST /search` — `{query_vector, user_id, top_k, file_ids?}` → `{results}`
- `DELETE /session/{user_id}/{session_id}`
- `DELETE /file/{user_id}/{file_id}`

## Run standalone (spins up its own Qdrant)
```bash
cp .env.example .env
docker compose up --build
```

## Local dev
Live-reload override + editable `add-ai-core` install, same pattern as
the other services. Point `QDRANT_URL` at the `qdrant` service from this
repo's own compose file, or at the shared one from
`add-ai-orchestration` if you're running the whole platform.

## Swapping vector DBs
Write a new `IVectorStore` implementation (e.g. `PgVectorStore`,
`PineconeVectorStore`) in `app/store.py`, wire it into `app/main.py`.
Nothing else in the platform changes — every caller only speaks the HTTP
contract above.
