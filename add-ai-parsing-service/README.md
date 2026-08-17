# add-ai-parsing-service

PDF (pdfplumber → pypdf rotation fallback → Tesseract OCR),
DOCX, TXT, and image-OCR document parsing + recursive chunking + a
chunk-audit log. Implements `IDocumentParser` / `IDocumentChunker` from
`add-ai-core`. This is the CPU-heaviest, most native-dependency-laden
adapter (needs `tesseract-ocr` installed at the OS level) — a natural
place to isolate its own image so the rest of the platform doesn't carry
that weight.

## API
`POST /parse` (multipart) — fields: `file`, `user_id`, `session_id`,
`file_id` → `{"chunks": [{"content": "...", "metadata": {...}}]}`

## Run standalone
```bash
cp .env.example .env
docker compose up --build
curl -X POST localhost:8006/parse \
  -F "file=@/path/to/sample.pdf" \
  -F "user_id=u1" -F "session_id=s1" -F "file_id=f1"
```

## Local dev
Live-reload override, same pattern as the other services.

## Note on scope
This service intentionally does NOT talk to the embedding model, vector
store, or BM25 index — it only turns a file into text chunks. Wiring
those together (parse → embed → upsert → index) is the
`IngestionService`'s job, which lives in `add-ai-backend` / `add-ai-worker`
and calls this service plus `add-ai-embeddings-service`,
`add-ai-vectorstore-service`, and `add-ai-sparseindex-service` in
sequence over HTTP.
