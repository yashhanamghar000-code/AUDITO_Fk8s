import pytest

from app.clients.null_tts_client import NullTtsClient
from app.core.interfaces.tts_client import ITTSClient, TTSUnavailableError
from app.services.tts_service import TTSService


class FakeTTSClient(ITTSClient):
    """Stand-in adapter used only to prove TTSService talks to the
    ITTSClient interface, not to any concrete class."""

    def __init__(self, audio: bytes = b"fake-mp3-bytes"):
        self._audio = audio
        self.last_text = None

    def synthesize(self, text: str, voice: str | None = None) -> bytes:
        self.last_text = text
        return self._audio

    def is_available(self) -> bool:
        return True


def test_speak_sanitizes_markdown_before_synthesis():
    fake = FakeTTSClient()
    service = TTSService(tts_client=fake)

    service.speak("**Hello** `world` [1]\n# Heading\n\n\nmore text")

    assert "**" not in fake.last_text
    assert "`" not in fake.last_text
    assert "[1]" not in fake.last_text
    assert "# " not in fake.last_text


def test_speak_replaces_code_blocks_with_a_speakable_placeholder():
    fake = FakeTTSClient()
    service = TTSService(tts_client=fake)

    service.speak("```print('hi')```")

    assert "```" not in fake.last_text
    assert "code block omitted" in fake.last_text


def test_speak_rejects_empty_after_sanitization():
    service = TTSService(tts_client=FakeTTSClient())
    with pytest.raises(ValueError):
        service.speak("   \n\n   ")


def test_null_client_reports_unavailable_and_raises_clean_error():
    service = TTSService(tts_client=NullTtsClient())

    assert service.is_available() is False
    with pytest.raises(TTSUnavailableError):
        service.speak("hello")


def test_null_client_is_a_valid_ittsclient_substitute():
    # Liskov substitution: NullTtsClient and any real adapter must be
    # interchangeable wherever ITTSClient is expected.
    assert isinstance(NullTtsClient(), ITTSClient)
    assert isinstance(FakeTTSClient(), ITTSClient)
