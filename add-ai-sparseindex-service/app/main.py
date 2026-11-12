import os
from typing import Any, Dict, List, Optional

from add_ai_core.entities.document import DocumentChunk
from fastapi import FastAPI
from pydantic import BaseModel

from app.index import Bm25SparseIndex

app = FastAPI(title="add-ai-sparseindex-service")

_index = Bm25SparseIndex(os.getenv("BM25_CACHE_DIR", "/data/bm25_cache"))


class Chunk(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}


class AddDocumentsRequest(BaseModel):
    user_id: str
    chunks: List[Chunk]


class SearchRequest(BaseModel):
    user_id: str
    query: str
    top_k: int = 15
    file_ids: Optional[List[str]] = None


class SearchResponse(BaseModel):
    results: List[Chunk]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents")
def add_documents(req: AddDocumentsRequest):
    chunks = [DocumentChunk(content=c.content, metadata=c.metadata) for c in req.chunks]
    _index.add_documents(req.user_id, chunks)
    return {"added": len(chunks)}


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    results = _index.search(req.user_id, req.query, req.top_k, req.file_ids)
    return SearchResponse(results=[Chunk(content=c.content, metadata=c.metadata) for c in results])


@app.delete("/file/{user_id}/{file_id}")
def remove_file(user_id: str, file_id: str):
    _index.remove_file(user_id, file_id)
    return {"deleted": "file"}
