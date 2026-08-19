/**
 * NEW FILE — src/types/speech.d.ts
 *
 * The Web Speech API's SpeechRecognition interface isn't part of
 * TypeScript's bundled DOM lib, and Chrome (the only major browser that
 * currently ships it) still exposes it under the vendor-prefixed name
 * `webkitSpeechRecognition`. This declares just enough of the shape for
 * useSpeechToText.ts to use it type-safely, without pulling in a full
 * @types package for an API this small.
 */

interface SpeechRecognitionResultLike {
  isFinal: boolean;
  [index: number]: { transcript: string };
  length: number;
}

interface SpeechRecognitionResultListLike {
  [index: number]: SpeechRecognitionResultLike;
  length: number;
}

interface SpeechRecognitionEventLike extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultListLike;
}

interface SpeechRecognitionLike extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: Event) => void) | null;
  onend: (() => void) | null;
}

interface Window {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
}
