FROM python:3.11-slim

WORKDIR /srv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 \
    HF_HOME=/models/huggingface

# add-ai-core: shared internal library, vendored from the monorepo build
# context instead of pulled from GitHub (works offline / without git
# credentials -- e.g. Jenkins agents that can't reach the private repo)
COPY add-ai-core /tmp/add-ai-core
RUN pip install --no-cache-dir /tmp/add-ai-core

COPY add-ai-embeddings-service/requirements.txt .

# Install CPU-only PyTorch separately
RUN pip install --upgrade pip && \
    pip install torch==2.5.1 \
        --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install \
    fastapi==0.115.0 \
    uvicorn[standard]==0.30.6 \
    pydantic==2.9.2 \
    langchain-huggingface==0.1.2 \
    sentence-transformers==3.1.1

COPY add-ai-embeddings-service/app ./app

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
