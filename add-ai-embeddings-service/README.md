# add-ai-embeddings-service

Turns text into dense vectors (HuggingFace `BAAI/bge-small-en-v1.5` by
default). Implements the `IEmbeddingProvider` contract from
[`add-ai-core`](https://github.com/<you>/add-ai-core), exposed over HTTP
instead of being imported in-process.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/health` | – | `{status, model}` |
| POST | `/embed/documents` | `{"texts": ["...", "..."]}` | `{"vectors": [[...], ...]}` |
| POST | `/embed/query` | `{"text": "..."}` | `{"vector": [...]}` |

## Run it locally (no other repo needed)

```bash
cp .env.example .env
docker compose up --build
curl -X POST localhost:8001/embed/query -H 'content-type: application/json' \
  -d '{"text": "hello world"}'
```

## Local development (live reload + editable core lib)

Check out `add-ai-core` as a sibling folder to this repo:

```
workspace/
├── add-ai-core/
└── add-ai-embeddings-service/
```

`docker-compose.override.yml` is picked up automatically by `docker
compose up` and will:
- bind-mount `./app` so code edits are reflected without a rebuild
- bind-mount `../add-ai-core` and `pip install -e` it, so contract
  changes there show up here immediately too
- run uvicorn with `--reload`

```bash
docker compose up --build
# edit app/main.py or app/provider.py — the running container reloads
```

Prefer running it outside Docker entirely for the fastest inner loop:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../add-ai-core
uvicorn app.main:app --reload --port 8001
```

## Testing

```bash
pip install pytest httpx
pytest
```

## Swapping the embedding model/provider

Change `EMBEDDING_MODEL` in `.env` for a different HuggingFace model with
no code changes. To swap providers entirely (e.g. OpenAI embeddings),
write a new class implementing `IEmbeddingProvider` in `app/provider.py`
and wire it into `app/main.py` — nothing outside this repo needs to
change, since every caller only ever talks to the HTTP contract above.
