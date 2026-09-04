# add-ai-llm-service

Thin HTTP wrapper around the Mistral chat-completion API.
Implements `ILLMClient` from `add-ai-core`. All prompt engineering stays
in the caller (`add-ai-backend`'s `chat_workflow_service`) — this service
only knows how to talk to Mistral.

## API
POST `/complete` — `{"messages": [{"role": "system"|"user", "content": "..."}]}`
→ `{"text": "..."}`

## Run standalone
```bash
cp .env.example .env   # fill in MISTRAL_API_KEY
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

## Jenkins and Kubernetes
Store the key in Jenkins Credentials as a **Secret text** credential with ID
`mistral-api-key`. In the deploy stage, bind it as `MISTRAL_API_KEY` and run:

```bash
kubectl -n audito create secret generic llm-service-secret \
  --from-literal=MISTRAL_API_KEY="$MISTRAL_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f k8s/llm-service-config.yaml -f k8s/llm-service.yaml
kubectl -n audito rollout restart deployment/llm-service
kubectl -n audito rollout status deployment/llm-service
```

The key must not be placed in the ConfigMap, Kubernetes YAML, Jenkinsfile, or Git.
