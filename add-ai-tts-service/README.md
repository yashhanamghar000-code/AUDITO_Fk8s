# add-ai-tts-service

Turns text (an assistant answer) into spoken audio (MP3), using Microsoft
Edge's free neural voices via [`edge-tts`](https://github.com/rany2/edge-tts).
No API key required, no model to load into memory — same "stateless HTTP
adapter" shape as `add-ai-embeddings-service`, just fronting a remote
websocket call instead of an in-process model.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/health` | – | `{status, voice}` |
| GET | `/voices` | – | curated list of `{id, label}` voices |
| POST | `/synthesize` | `{"text": "...", "voice"?: "...", "rate"?: "+0%", "pitch"?: "+0Hz"}` | `audio/mpeg` bytes |

`text` longer than `TTS_MAX_CHARS` (default 4000) is truncated server-side.

## Run it locally (no other repo needed)

```bash
docker compose up --build
curl -X POST localhost:8009/synthesize -H 'content-type: application/json' \
  -d '{"text": "hello world"}' --output out.mp3
```

## Env vars

| Var | Default |
|---|---|
| `TTS_VOICE` | `en-US-AriaNeural` |
| `TTS_RATE` | `+0%` |
| `TTS_PITCH` | `+0Hz` |
| `TTS_MAX_CHARS` | `4000` |
