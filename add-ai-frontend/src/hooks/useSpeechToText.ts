import { useCallback, useEffect, useRef, useState } from "react";

// Minimal shape of the parts of the Web Speech API this hook uses — not
// shipped in standard TS lib.dom yet, and prefixed on some browsers.
interface SpeechRecognitionResultLike {
  isFinal: boolean;
  0: { transcript: string };
}
interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: ArrayLike<SpeechRecognitionResultLike>;
}
interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((e: SpeechRecognitionEventLike) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
}

function getSpeechRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === "undefined") return null;
  const w = window as any;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export interface UseSpeechToTextOptions {
  lang?: string;
  // Called with the live (interim + final) transcript as the person speaks.
  onTranscript?: (text: string, isFinal: boolean) => void;
}

export interface UseSpeechToTextResult {
  isSupported: boolean;
  isListening: boolean;
  start: () => void;
  stop: () => void;
  toggle: () => void;
}

/**
 * Provider-agnostic speech-to-text. Today this wraps the browser's
 * built-in SpeechRecognition (free, zero backend calls, but Chrome/Edge
 * only). If a backend STT service is added later (e.g. mirroring
 * add-ai-tts-service), only this hook's internals need to change —
 * ChatInput consumes { isSupported, isListening, start, stop, toggle }
 * regardless of what implements them.
 */
export function useSpeechToText(options: UseSpeechToTextOptions = {}): UseSpeechToTextResult {
  const { lang = "en-US", onTranscript } = options;
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const Ctor = getSpeechRecognitionCtor();
  const isSupported = Ctor !== null;

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  const start = useCallback(() => {
    if (!Ctor || recognitionRef.current) return;

    const recognition = new Ctor();
    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (e) => {
      let text = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const result = e.results[i];
        text += result[0].transcript;
        onTranscript?.(text, result.isFinal);
      }
    };
    recognition.onerror = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };
    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, [Ctor, lang, onTranscript]);

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    setIsListening(false);
  }, []);

  const toggle = useCallback(() => {
    if (isListening) stop();
    else start();
  }, [isListening, start, stop]);

  return { isSupported, isListening, start, stop, toggle };
}
