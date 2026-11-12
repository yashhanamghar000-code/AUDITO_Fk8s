from app.core.interfaces.tts_client import ITTSClient, TTSUnavailableError


class NullTtsClient(ITTSClient):
    """Used when TTS_ENABLED=false or no TTS_SERVICE_URL is configured.

    Without this, every caller of ITTSClient would need an `if tts_client
    is not None` check scattered around. With it, container.py makes the
    ONE decision (real adapter vs. this no-op) and everything downstream —
    TTSService, the router — stays exactly the same regardless of whether
    the feature is on, off, or the service was deleted entirely."""

    def synthesize(self, text: str, voice: str | None = None) -> bytes:
        raise TTSUnavailableError("Text-to-speech is not enabled on this deployment.")

    def is_available(self) -> bool:
        return False
