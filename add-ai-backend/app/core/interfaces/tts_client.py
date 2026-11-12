from abc import ABC, abstractmethod


class ITTSClient(ABC):
    """Contract for anything that can turn text into spoken audio bytes.

    TTSService (and the router above it) depend on this abstraction only —
    never on TtsServiceClient or any other concrete adapter directly. That
    means:
      - swapping add-ai-tts-service for a different provider (ElevenLabs,
        OpenAI TTS, a local model, ...) means writing ONE new class here
        and changing ONE line in container.py — nothing else in the
        codebase needs to know:
      - disabling/removing the feature entirely means pointing container.py
        at NullTtsClient instead — the router and service code are
        unchanged, they just get a clean "unavailable" error instead of a
        connection failure.
    """

    @abstractmethod
    def synthesize(self, text: str, voice: str | None = None) -> bytes:
        """Return audio bytes (mp3) for `text`, or raise TTSUnavailableError."""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """Cheap check the router/frontend can use to decide whether to
        show the feature at all, without attempting a real synthesis."""
        raise NotImplementedError


class TTSUnavailableError(RuntimeError):
    """Raised by any ITTSClient implementation when synthesis can't be
    performed right now (service disabled, unreachable, or erroring) —
    a single exception type callers can catch regardless of which
    concrete adapter is wired in."""
