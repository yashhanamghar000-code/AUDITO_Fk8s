FROM python:3.11-slim
WORKDIR /srv

# add-ai-core: shared internal library, vendored from the monorepo build
# context instead of pulled from GitHub (works offline / without git
# credentials -- e.g. Jenkins agents that can't reach the private repo)
COPY add-ai-core /tmp/add-ai-core
RUN pip install --no-cache-dir /tmp/add-ai-core

# tesseract-ocr is a native dependency of pytesseract (OCR fallback for
# scanned/rotated PDF pages) -- this is exactly why parsing is worth its
# own image: it needs system packages nothing else in the platform does.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential tesseract-ocr libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY add-ai-parsing-service/requirements.txt .
RUN pip install -r requirements.txt

COPY add-ai-parsing-service/app ./app
ENV DEBUG_LOGS_DIR=/data/debug_logs
EXPOSE 8006
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]
