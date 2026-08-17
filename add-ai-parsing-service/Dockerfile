FROM python:3.11-slim
WORKDIR /srv

# tesseract-ocr is a native dependency of pytesseract (OCR fallback for
# scanned/rotated PDF pages) — this is exactly why parsing is worth its
# own image: it needs system packages nothing else in the platform does.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential tesseract-ocr libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
ENV DEBUG_LOGS_DIR=/data/debug_logs
EXPOSE 8006
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]
