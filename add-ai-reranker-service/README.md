# add-ai-reranker-service

Re-scores a candidate set of chunks against a query using a local
CrossEncoder model. Implements `IReranker` from `add-ai-core`, exposed
over HTTP.

## API
POST `/rerank` — `{"query": "...", "candidates": [{"content": "...", "metadata": {}}], "top_n": 6}`
→ `{"results": [...]}` (most relevant first)

## Run standalone
```bash
cp .env.example .env
docker compose up --build
```

## Local dev (live reload)
Same pattern as `add-ai-embeddings-service`: check out `add-ai-core` as a
sibling folder, then `docker compose up --build` picks up
`docker-compose.override.yml` automatically for bind-mounted, reloading
code. Or run outside Docker:
```bash
pip install -r requirements.txt && pip install -e ../add-ai-core
uvicorn app.main:app --reload --port 8002
```
