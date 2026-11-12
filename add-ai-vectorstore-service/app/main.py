import os
from typing import Any, Dict, List, Optional

from add_ai_core.entities.document import DocumentChunk
from fastapi import FastAPI
from pydantic import BaseModel

from app.store import QdrantVectorStore

app = FastAPI(title="add-ai-vectorstore-service")

_store = QdrantVectorStore(
    url=os.environ["QDRANT_URL"],
    api_key=os.getenv("QDRANT_API_KEY"),
    collection_name=os.getenv("QDRANT_COLLECTION_NAME", "audito_documents"),
    embedding_dim=int(os.getenv("EMBEDDING_DIM", "384")),
)


class Chunk(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}


class UpsertRequest(BaseModel):
    chunks: List[Chunk]
    vectors: List[List[float]]
    user_id: str
    session_id: str


class SearchRequest(BaseModel):
    query_vector: List[float]
    user_id: str
    top_k: int = 15
    file_ids: Optional[List[str]] = None


class SearchResponse(BaseModel):
    results: List[Chunk]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upsert")
def upsert(req: UpsertRequest):
    chunks = [DocumentChunk(content=c.content, metadata=c.metadata) for c in req.chunks]
    _store.upsert(chunks, req.vectors, req.user_id, req.session_id)
    return {"upserted": len(chunks)}


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    results = _store.search(req.query_vector, req.user_id, req.top_k, req.file_ids)
    return SearchResponse(results=[Chunk(content=c.content, metadata=c.metadata) for c in results])


@app.delete("/session/{user_id}/{session_id}")
def delete_session(user_id: str, session_id: str):
    _store.delete_session(user_id, session_id)
    return {"deleted": "session"}


@app.delete("/file/{user_id}/{file_id}")
def delete_file(user_id: str, file_id: str):
    _store.delete_file(user_id, file_id)
    return {"deleted": "file"}
