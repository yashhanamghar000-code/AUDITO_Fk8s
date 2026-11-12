import os
from typing import Any, Dict, List

from add_ai_core.entities.document import DocumentChunk
from fastapi import FastAPI
from pydantic import BaseModel

from app.reranker import CrossEncoderReranker

MODEL_NAME = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

app = FastAPI(title="add-ai-reranker-service")
_reranker = CrossEncoderReranker(MODEL_NAME)


class Candidate(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}


class RerankRequest(BaseModel):
    query: str
    candidates: List[Candidate]
    top_n: int = 6


class RerankResponse(BaseModel):
    results: List[Candidate]


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/rerank", response_model=RerankResponse)
def rerank(req: RerankRequest):
    chunks = [DocumentChunk(content=c.content, metadata=c.metadata) for c in req.candidates]
    top = _reranker.rerank(req.query, chunks, req.top_n)
    return RerankResponse(results=[Candidate(content=c.content, metadata=c.metadata) for c in top])
