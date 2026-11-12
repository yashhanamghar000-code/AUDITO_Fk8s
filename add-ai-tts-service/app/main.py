"""
add-ai-tts-service
Wraps EdgeTTSProvider behind a small HTTP API so text-to-speech can be
built, deployed, and scaled as its own container, independent of every
other adapter — same shape as add-ai-embeddings-service.
"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.provider import EdgeTTSProvider

DEFAULT_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")
DEFAULT_RATE = os.getenv("TTS_RATE", "+0%")
DEFAULT_PITCH = os.getenv("TTS_PITCH", "+0Hz")
MAX_CHARS = int(os.getenv("TTS_MAX_CHARS", "4000"))

app = FastAPI(title="add-ai-tts-service")

_provider = EdgeTTSProvider(DEFAULT_VOICE, DEFAULT_RATE, DEFAULT_PITCH)


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: str | None = None
    rate: str | None = None
    pitch: str | None = None


@app.get("/health")
def health():
    return {"status": "ok", "voice": DEFAULT_VOICE}


@app.get("/voices")
def voices():
    # A short curated list rather than the full ~400 edge-tts voices —
    # enough for the frontend to offer a voice picker later without
    # shipping the entire catalog on every request.
    return {
        "voices": [
            {"id": "en-US-AriaNeural", "label": "Aria (US, female)"},
            {"id": "en-US-GuyNeural", "label": "Guy (US, male)"},
            {"id": "en-US-JennyNeural", "label": "Jenny (US, female)"},
            {"id": "en-GB-SoniaNeural", "label": "Sonia (UK, female)"},
            {"id": "en-GB-RyanNeural", "label": "Ryan (UK, male)"},
            {"id": "en-IN-NeerjaNeural", "label": "Neerja (India, female)"},
            {"id": "en-IN-PrabhatNeural", "label": "Prabhat (India, male)"},
        ]
    }


@app.post("/synthesize")
def synthesize(req: SynthesizeRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text must not be empty")
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS]

    try:
        audio_bytes = _provider.synthesize_sync(text, req.voice, req.rate, req.pitch)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"TTS synthesis failed: {e}")

    if not audio_bytes:
        raise HTTPException(status_code=502, detail="TTS synthesis returned no audio")

    return Response(content=audio_bytes, media_type="audio/mpeg")
