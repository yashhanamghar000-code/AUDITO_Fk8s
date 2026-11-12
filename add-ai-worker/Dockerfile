FROM python:3.11-slim
WORKDIR /srv

# add-ai-core: shared internal library, vendored from the monorepo build
# context instead of pulled from GitHub (works offline / without git
# credentials -- e.g. Jenkins agents that can't reach the private repo)
COPY add-ai-core /tmp/add-ai-core
RUN pip install --no-cache-dir /tmp/add-ai-core

COPY add-ai-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY add-ai-worker/app ./app
# concurrency=3: several users' uploads can ingest in parallel without
# one large file blocking everyone else's. Scale further with
# `docker compose up --scale worker=3` once this is deployed.
CMD ["celery", "-A", "app.celery_app.celery_app", "worker", "--loglevel=info", "--concurrency=3"]
