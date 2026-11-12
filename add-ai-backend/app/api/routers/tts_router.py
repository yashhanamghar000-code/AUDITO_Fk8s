import traceback
from types import SimpleNamespace

from fastapi import APIRouter, Depends, Form, HTTPException, Response

from app.api.dependencies import get_container, get_current_user
from app.container import Container
from app.core.interfaces.tts_client import TTSUnavailableError

router = APIRouter(prefix="/api/tts", tags=["tts"])


@router.get("/status")
def tts_status(container: Container = Depends(get_container)):
    # Lets the frontend decide whether to show the speaker icon at all —
    # true regardless of whether TTS is off (NullTtsClient) or the real
    # service is just unreachable right now.
    return {"available": container.tts_service.is_available()}


@router.post("/speak")
async def speak(
    text: str = Form(...),
    voice: str | None = Form(None),
    container: Container = Depends(get_container),
    current_user: SimpleNamespace = Depends(get_current_user),
):
    try:
        audio_bytes = container.tts_service.speak(text, voice=voice)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except TTSUnavailableError as e:
        # Feature disabled or the microservice is down — a clean 503, not
        # a 500, so the frontend can treat it as "hide the button" rather
        # than an unexpected error.
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"TTS Error: {str(e)}")
