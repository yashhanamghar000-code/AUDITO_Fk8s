# add-ai-llm-service

Thin HTTP wrapper around the Azure OpenAI chat-completion client.
Implements `ILLMClient` from `add-ai-core`. All prompt engineering stays
in the caller (`add-ai-backend`'s `chat_workflow_service`) — this service
only knows how to talk to Azure.

## API
POST `/complete` — `{"messages": [{"role": "system"|"user", "content": "..."}]}`
→ `{"text": "..."}`

## Run standalone
```bash
cp .env.example .env   # fill in MY_API_KEY / AZURE_OPENAI_ENDPOINT
docker compose up --build
curl -X POST localhost:8003/complete -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"say hi"}]}'
```

## Local dev
Same live-reload pattern as the other services — see
`docker-compose.override.yml`, or run outside Docker:
```bash
pip install -r requirements.txt && pip install -e ../add-ai-core
uvicorn app.main:app --reload --port 8003
```

## Swapping providers
Write a new `Ixxx`-compliant client class in `app/client.py` (e.g.
`OpenAiLlmClient`, `AnthropicLlmClient`) and point `app/main.py` at it —
no other repo needs to change since they only ever call `POST /complete`.
