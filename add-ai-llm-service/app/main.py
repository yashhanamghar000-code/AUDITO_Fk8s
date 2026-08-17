import os
from typing import List, Tuple

from fastapi import FastAPI
from pydantic import BaseModel

from app.client import AzureLlmClient

app = FastAPI(title="add-ai-llm-service")

_client = AzureLlmClient(
    deployment=os.environ["AZURE_LLM_DEPLOYMENT"],
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    api_key=os.environ["MY_API_KEY"],
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
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
