#!/usr/bin/env bash
# Builds every sibling repo's image locally, tagged exactly as
# docker-compose.yml expects (`<repo>:local`). Run this after cloning
# every repo as a sibling of add-ai-orchestration:
#
#   workspace/
#   ├── add-ai-orchestration/   (you are here)
#   ├── add-ai-core/
#   ├── add-ai-frontend/
#   ├── add-ai-backend/
#   ├── add-ai-worker/
#   ├── add-ai-auth-service/
#   ├── add-ai-data-service/
#   ├── add-ai-embeddings-service/
#   ├── add-ai-reranker-service/
#   ├── add-ai-llm-service/
#   ├── add-ai-vectorstore-service/
#   ├── add-ai-sparseindex-service/
#   └── add-ai-parsing-service/
set -euo pipefail

REPOS=(
  add-ai-frontend
  add-ai-backend
  add-ai-worker
  add-ai-auth-service
  add-ai-data-service
  add-ai-embeddings-service
  add-ai-reranker-service
  add-ai-llm-service
  add-ai-vectorstore-service
  add-ai-sparseindex-service
  add-ai-parsing-service
)

for repo in "${REPOS[@]}"; do
  path="../$repo"
  if [ ! -d "$path" ]; then
    echo "!!  $path not found — clone it as a sibling of this repo first. Skipping." >&2
    continue
  fi
  echo "==> Building $repo:local"
  docker build -t "$repo:local" "$path"
done

echo
echo "All images built. Run: docker compose up"
