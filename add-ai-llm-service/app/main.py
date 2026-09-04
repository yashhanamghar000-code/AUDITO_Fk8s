import os
from typing import List, Tuple

from fastapi import FastAPI
from pydantic import BaseModel

from app.client import MistralLlmClient

app = FastAPI(title="add-ai-llm-service")

_client = MistralLlmClient(
    model=os.getenv("MISTRAL_MODEL", "mistral-large-latest"),
    api_key=os.environ["MISTRAL_API_KEY"],
    endpoint=os.getenv("MISTRAL_ENDPOINT", "https://api.mistral.ai/v1"),
    temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
)


class Message(BaseModel):
    role: str  # "system" | "user"
    content: str


class CompleteRequest(BaseModel):
    messages: List[Message]


class CompleteResponse(BaseModel):
    text: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/complete", response_model=CompleteResponse)
def complete(req: CompleteRequest):
    pairs: List[Tuple[str, str]] = [(m.role, m.content) for m in req.messages]
    return CompleteResponse(text=_client.complete(pairs))
