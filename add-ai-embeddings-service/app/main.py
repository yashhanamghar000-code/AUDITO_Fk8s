"""
add-ai-embeddings-service
Wraps HuggingFaceEmbeddingProvider (implements IEmbeddingProvider from
add-ai-core) behind a small HTTP API so it can be built, deployed, and
scaled as its own container, independent of every other adapter.
"""
import os
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

from app.provider import HuggingFaceEmbeddingProvider

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

app = FastAPI(title="add-ai-embeddings-service")

# Loaded once at process start (heavy: downloads/loads the model into
# memory) and shared across every request in this container.
_provider = HuggingFaceEmbeddingProvider(MODEL_NAME)


class EmbedDocumentsRequest(BaseModel):
    texts: List[str]


class EmbedDocumentsResponse(BaseModel):
    vectors: List[List[float]]


class EmbedQueryRequest(BaseModel):
    text: str


class EmbedQueryResponse(BaseModel):
    vector: List[float]


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/embed/documents", response_model=EmbedDocumentsResponse)
def embed_documents(req: EmbedDocumentsRequest):
    return EmbedDocumentsResponse(vectors=_provider.embed_documents(req.texts))


@app.post("/embed/query", response_model=EmbedQueryResponse)
def embed_query(req: EmbedQueryRequest):
    return EmbedQueryResponse(vector=_provider.embed_query(req.text))
