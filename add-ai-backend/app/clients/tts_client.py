import httpx

from app.core.interfaces.tts_client import ITTSClient, TTSUnavailableError


class TtsServiceClient(ITTSClient):
    """HTTP adapter for add-ai-tts-service. This is the ONE file that knows
    that microservice exists — same rule as ResendEmailSender for Resend.
    Swapping the TTS provider means writing a new ITTSClient implementation
    and changing one line in container.py."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self._client = httpx.Client(base_url=base_url, timeout=timeout)

    def synthesize(self, text: str, voice: str | None = None) -> bytes:
        payload = {"text": text}
        if voice:
            payload["voice"] = voice
        try:
            r = self._client.post("/synthesize", json=payload)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise TTSUnavailableError(f"add-ai-tts-service request failed: {e}") from e
        return r.content

    def is_available(self) -> bool:
        try:
            r = self._client.get("/health", timeout=3.0)
            return r.status_code == 200
        except httpx.HTTPError:
            return False
