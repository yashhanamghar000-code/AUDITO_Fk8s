import re

from app.core.interfaces.tts_client import ITTSClient, TTSUnavailableError

# Matches the fenced-code, markdown, and citation-marker conventions the
# frontend renders (see MessageBubble.tsx / ReactMarkdown + CitationChip) —
# none of that reads naturally aloud, so it's stripped before synthesis.
_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]*)`")
_MD_HEADING_RE = re.compile(r"^#{1,6}\s*", re.MULTILINE)
_MD_BOLD_ITALIC_RE = re.compile(r"(\*\*\*|\*\*|\*|___|__|_)")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_CITATION_MARKER_RE = re.compile(r"\[\d+\]")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_MULTI_NEWLINE_RE = re.compile(r"\n{2,}")


class TTSService:
    """Turns a stored assistant answer into spoken audio. Sits in the
    service layer (not the client) because "make this readable aloud" is
    business logic specific to how AUDITO renders answers — the TTS
    adapter itself has no opinion on markdown.

    Depends only on ITTSClient (constructor injection) — never imports
    TtsServiceClient or NullTtsClient directly. That's what makes this
    class indifferent to whether TTS is enabled, which provider backs it,
    or whether the service exists at all; container.py is the only place
    that decision gets made.
    """

    MAX_CHARS = 4000

    def __init__(self, tts_client: ITTSClient):
        self._client = tts_client

    def is_available(self) -> bool:
        return self._client.is_available()

    def speak(self, text: str, voice: str | None = None) -> bytes:
        clean = self._sanitize(text)
        # Guards against inputs that are technically non-empty after
        # sanitization but carry no real content — e.g. blank lines
        # collapse into a stray "." — which would otherwise reach the
        # TTS engine as a pointless one-character synthesis request.
        if not clean or not re.search(r"[A-Za-z0-9]", clean):
            raise ValueError("Nothing speakable in this message.")
        try:
            return self._client.synthesize(clean[: self.MAX_CHARS], voice=voice)
        except TTSUnavailableError:
            raise

    @staticmethod
    def _sanitize(text: str) -> str:
        t = _CODE_BLOCK_RE.sub(" code block omitted. ", text)
        t = _INLINE_CODE_RE.sub(r"\1", t)
        t = _MD_HEADING_RE.sub("", t)
        t = _MD_LINK_RE.sub(r"\1", t)
        t = _CITATION_MARKER_RE.sub("", t)
        t = _MD_BOLD_ITALIC_RE.sub("", t)
        t = _MULTI_NEWLINE_RE.sub(". ", t)
        t = _MULTI_SPACE_RE.sub(" ", t)
        return t.strip()
