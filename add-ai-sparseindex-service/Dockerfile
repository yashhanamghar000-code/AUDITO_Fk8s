FROM python:3.11-slim
WORKDIR /srv

# add-ai-core: shared internal library, vendored from the monorepo build
# context instead of pulled from GitHub (works offline / without git
# credentials -- e.g. Jenkins agents that can't reach the private repo)
COPY add-ai-core /tmp/add-ai-core
RUN pip install --no-cache-dir /tmp/add-ai-core

COPY add-ai-sparseindex-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY add-ai-sparseindex-service/app ./app
EXPOSE 8005
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
