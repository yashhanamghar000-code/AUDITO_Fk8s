import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ttsService } from "@/services/tts";
import { toast } from "sonner";

export type TTSPlaybackState = "idle" | "loading" | "playing";

interface TTSContextValue {
  // False whenever the backend feature is off (NullTtsClient), the
  // tts-service container is stopped/removed, or the probe failed —
  // components branch on this ONE flag instead of each guessing.
  available: boolean;
  playingMessageId: string | null;
  playbackState: TTSPlaybackState;
  // Toggle play/stop for a given message. Starting a new one stops
  // whatever was already playing, so at most one answer speaks at a time.
  toggleSpeak: (messageId: string, text: string) => void;
  stop: () => void;
}

const TTSContext = createContext<TTSContextValue | null>(null);

export function TTSProvider({ children }: { children: ReactNode }) {
  const [available, setAvailable] = useState(false);
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [playbackState, setPlaybackState] = useState<TTSPlaybackState>("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    ttsService
      .status()
      .then((res) => setAvailable(res.data.available))
      .catch(() => setAvailable(false));
  }, []);

  const cleanupAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.onended = null;
      audioRef.current.onerror = null;
      audioRef.current = null;
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
  }, []);

  const stop = useCallback(() => {
    requestIdRef.current += 1; // invalidates any in-flight fetch's result
    cleanupAudio();
    setPlayingMessageId(null);
    setPlaybackState("idle");
  }, [cleanupAudio]);

  useEffect(() => stop, [stop]); // stop + revoke on unmount

  const toggleSpeak = useCallback(
    (messageId: string, text: string) => {
      if (!available) return;

      // Already playing/loading this exact message — treat as Stop.
      if (playingMessageId === messageId) {
        stop();
        return;
      }

      // Switching to a different message: stop whatever was playing first.
      stop();
      const thisRequestId = requestIdRef.current;
      setPlayingMessageId(messageId);
      setPlaybackState("loading");

      ttsService
        .speak(text)
        .then((res) => {
          if (thisRequestId !== requestIdRef.current) return; // superseded
          const url = URL.createObjectURL(res.data);
          objectUrlRef.current = url;
          const audio = new Audio(url);
          audioRef.current = audio;
          audio.onended = () => {
            if (thisRequestId === requestIdRef.current) stop();
          };
          audio.onerror = () => {
            if (thisRequestId === requestIdRef.current) {
              toast.error("Couldn't play audio for this answer.");
              stop();
            }
          };
          setPlaybackState("playing");
          audio.play().catch(() => {
            if (thisRequestId === requestIdRef.current) stop();
          });
        })
        .catch((err) => {
          if (thisRequestId !== requestIdRef.current) return;
          if (err?.response?.status === 503) {
            // Feature just went unavailable mid-session — hide the UI
            // for everyone else too instead of erroring again.
            setAvailable(false);
          } else {
            toast.error(err?.response?.data?.detail ?? "Couldn't generate audio for this answer.");
          }
          stop();
        });
    },
    [available, playingMessageId, stop],
  );

  const value: TTSContextValue = {
    available,
    playingMessageId,
    playbackState,
    toggleSpeak,
    stop,
  };

  return <TTSContext.Provider value={value}>{children}</TTSContext.Provider>;
}

export function useTTS() {
  const ctx = useContext(TTSContext);
  if (!ctx) throw new Error("useTTS must be used inside TTSProvider");
  return ctx;
}
