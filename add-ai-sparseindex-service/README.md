# add-ai-sparseindex-service

Per-user BM25 keyword retrieval, implements `ISparseIndex` from
`add-ai-core`. Backed by a pickle cache on a persistent volume
(`BM25_CACHE_DIR`) — this service is the only thing on the platform that
touches that volume, so its storage format can change without any other
repo caring.

## API
- `POST /documents` — `{user_id, chunks}`
- `POST /search` — `{user_id, query, top_k, file_ids?}` → `{results}`
- `DELETE /file/{user_id}/{file_id}`

## Run standalone
```bash
cp .env.example .env
docker compose up --build
```

## Local dev
Live-reload override, same pattern as the other services — see
`docker-compose.override.yml`.

## Swapping the sparse-index backend
Write a new `ISparseIndex` implementation (e.g.
`ElasticsearchSparseIndex`) in `app/index.py`, wire it into
`app/main.py`. No other repo changes.
