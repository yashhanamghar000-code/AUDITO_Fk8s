/**
 * NEW FILE — src/hooks/useTextToSpeech.ts
 *
 * "Read the answer aloud" — via the browser's built-in SpeechSynthesis
 * API. Same philosophy as useSpeechToText: no backend call, no new
 * microservice, no audio file generated or stored anywhere. This gets
 * lifted into ChatContext (not called per-MessageBubble) so there's a
 * single source of truth for "which message is currently playing" —
 * window.speechSynthesis is a single global player, so only one message
 * can genuinely be speaking at a time regardless of how many bubbles are
 * on screen, and the UI state needs to reflect that.
 */
import { useCallback, useEffect, useState } from "react";

export const isSpeechSynthesisSupported = () =>
  typeof window !== "undefined" && "speechSynthesis" in window;

/**
 * Strips markdown syntax before speaking — reading "hash hash Summary
 * asterisk asterisk" aloud verbatim is worse than useless. Keeps just the
 * words a person would actually want to hear.
 */
function toSpokenText(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, " ")        // fenced code blocks
    .replace(/`([^`]+)`/g, "$1")             // inline code
    .replace(/\[(.*?)\]\(.*?\)/g, "$1")      // [text](url) -> text
    .replace(/[#*_>~]/g, "")                 // markdown punctuation
    .replace(/\s+/g, " ")
    .trim();
}

export function useTextToSpeech() {
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [isSupported] = useState(isSpeechSynthesisSupported);

  // Stop any in-progress speech if the user navigates away/closes the tab.
  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, []);

  const stop = useCallback(() => {
    window.speechSynthesis?.cancel();
    setSpeakingId(null);
  }, []);

  const speak = useCallback((id: string, markdownText: string) => {
    if (!isSupported) return;
    window.speechSynthesis.cancel(); // only one message speaks at a time

    const text = toSpokenText(markdownText);
    if (!text) return;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.onend = () => setSpeakingId((current) => (current === id ? null : current));
    utterance.onerror = () => setSpeakingId((current) => (current === id ? null : current));

    setSpeakingId(id);
    window.speechSynthesis.speak(utterance);
  }, [isSupported]);

  const toggle = useCallback(
    (id: string, markdownText: string) => {
      if (speakingId === id) stop();
      else speak(id, markdownText);
    },
    [speakingId, speak, stop],
  );

  return { speakingId, isSupported, speak, stop, toggle };
}
