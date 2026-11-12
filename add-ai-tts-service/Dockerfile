FROM python:3.11-slim

WORKDIR /srv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TTS_VOICE=en-US-AriaNeural

COPY add-ai-tts-service/requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY add-ai-tts-service/app ./app

EXPOSE 8009

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8009"]
