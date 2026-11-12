import os
from typing import List, Tuple

from fastapi import FastAPI
from pydantic import BaseModel

from app.client import GeminiLlmClient


app = FastAPI(title="add-ai-llm-service")


_client = GeminiLlmClient(
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
    api_key=os.environ["GEMINI_API_KEY"],
    base_url=os.getenv(
        "GEMINI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    ),
    temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
)


class Message(BaseModel):
    role: str
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
    pairs: List[Tuple[str, str]] = [
        (m.role, m.content)
        for m in req.messages
    ]

    return CompleteResponse(
        text=_client.complete(pairs)
    )
