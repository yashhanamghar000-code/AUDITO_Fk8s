import { api } from "./api";

// Matches backend/app/api/routers/tts_router.py. Text-to-speech is an
// OPTIONAL backend feature (see add-ai-backend/app/container.py —
// ITTSClient / NullTtsClient): /status tells the frontend whether to show
// the speaker UI at all, and /speak degrades to a clean 503 rather than a
// hard failure when the feature is off or the service is unreachable.

export interface TTSStatusResponse {
  available: boolean;
}

export const ttsService = {
  status: () => api.get<TTSStatusResponse>("/api/tts/status"),

  // Returns an audio Blob (mp3) — responseType "blob" so axios doesn't try
  // to parse binary audio as JSON.
  speak: (text: string, voice?: string, signal?: AbortSignal) => {
    const form = new FormData();
    form.append("text", text);
    if (voice) form.append("voice", voice);
    return api.post<Blob>("/api/tts/speak", form, {
      responseType: "blob",
      signal,
    });
  },
};
