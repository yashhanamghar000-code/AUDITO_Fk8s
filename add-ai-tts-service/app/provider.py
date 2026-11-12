import asyncio
import io

import edge_tts


class EdgeTTSProvider:
    """Wraps Microsoft Edge's neural TTS voices (via the edge-tts library).

    No API key required and no model to load into memory — edge-tts just
    opens a websocket to Microsoft's public TTS endpoint per request, so
    unlike embeddings/reranker there is nothing heavy to warm up at
    process start.
    """

    def __init__(self, default_voice: str, default_rate: str, default_pitch: str):
        self._default_voice = default_voice
        self._default_rate = default_rate
        self._default_pitch = default_pitch

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        rate: str | None = None,
        pitch: str | None = None,
    ) -> bytes:
        communicate = edge_tts.Communicate(
            text,
            voice=voice or self._default_voice,
            rate=rate or self._default_rate,
            pitch=pitch or self._default_pitch,
        )
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        return buf.getvalue()

    def synthesize_sync(
        self,
        text: str,
        voice: str | None = None,
        rate: str | None = None,
        pitch: str | None = None,
    ) -> bytes:
        return asyncio.run(self.synthesize(text, voice, rate, pitch))
