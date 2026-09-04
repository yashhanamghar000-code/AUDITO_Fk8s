/**
 * NEW FILE — src/hooks/useSpeechToText.ts
 *
 * Voice input for the chat box, via the browser's built-in Web Speech
 * API (SpeechRecognition). No backend call, no new microservice, no
 * audio ever leaves the browser — the browser itself does the
 * transcription and hands back text. This is what powers the mic button
 * in ChatInput.tsx.
 *
 * Browser support: Chrome/Edge (desktop + Android) support this natively.
 * Firefox and Safari currently don't implement SpeechRecognition — the
 * hook degrades gracefully (`isSupported: false`), and ChatInput hides
 * the mic button entirely in that case rather than showing a button that
 * silently does nothing.
 */
import { useCallback, useEffect, useRef, useState } from "react";

function getSpeechRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

export const isSpeechRecognitionSupported = () => getSpeechRecognitionCtor() !== null;

interface UseSpeechToTextOptions {
  /** Called once per completed phrase, e.g. after a pause in speech. */
  onFinalResult?: (transcript: string) => void;
  lang?: string;
}

export function useSpeechToText({ onFinalResult, lang = "en-US" }: UseSpeechToTextOptions = {}) {
  const [isListening, setIsListening] = useState(false);
  const [isSupported] = useState(isSpeechRecognitionSupported);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const onFinalResultRef = useRef(onFinalResult);
  onFinalResultRef.current = onFinalResult;

  useEffect(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) return;

    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = lang;

    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          const transcript = result[0].transcript.trim();
          if (transcript) onFinalResultRef.current?.(transcript);
        }
      }
    };

    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;

    return () => {
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.abort();
      recognitionRef.current = null;
    };
  }, [lang]);

  const start = useCallback(() => {
    if (!recognitionRef.current || isListening) return;
    try {
      recognitionRef.current.start();
      setIsListening(true);
    } catch {
      // start() throws if called while already running (rapid double
      // click) — safe to ignore, state already reflects "listening".
    }
  }, [isListening]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  const toggle = useCallback(() => {
    if (isListening) stop();
    else start();
  }, [isListening, start, stop]);

  return { isSupported, isListening, start, stop, toggle };
}
