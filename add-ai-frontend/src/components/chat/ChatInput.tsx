import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { motion } from "framer-motion";
import { ArrowUp, Paperclip, Mic, MicOff, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useChat } from "@/contexts/ChatContext";
import { useSpeechToText } from "@/hooks/useSpeechToText";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export function ChatInput() {
  const { sendMessage, isStreaming, stopGeneration, uploadDocument } = useChat();
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  // Text captured in the box the moment mic listening starts — new speech
  // is appended after it rather than overwriting whatever was already typed.
  const baseTextRef = useRef("");

  const { isSupported: micSupported, isListening, toggle: toggleMic } = useSpeechToText({
    onTranscript: (transcript) => {
      const base = baseTextRef.current;
      setValue(base ? `${base} ${transcript}` : transcript);
    },
  });

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 220) + "px";
  }, [value]);

  async function submit() {
    const text = value.trim();
    if (!text || isStreaming) return;
    if (isListening) toggleMic();
    setValue("");
    await sendMessage(text);
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function onMicClick() {
    if (!isListening) baseTextRef.current = value.trim();
    toggleMic();
  }

  const canSend = value.trim().length > 0 && !isStreaming;

  return (
    <div className="relative">
      <input
        ref={fileRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          try {
            await uploadDocument(file);
            toast.success("Upload started");
          } catch (err) {
            toast.error(err instanceof Error ? err.message : "Upload failed");
          }
        }}
      />
      <div className="flex items-end gap-2 rounded-3xl border border-border bg-card p-2.5 shadow-sm transition-shadow focus-within:shadow-md">
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 shrink-0 rounded-full"
          onClick={() => fileRef.current?.click()}
          aria-label="Attach PDF"
        >
          <Paperclip className="h-4 w-4" />
        </Button>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            // Typing manually while mic is live re-anchors the base text,
            // so the next spoken chunk appends after what was just typed.
            if (isListening) baseTextRef.current = e.target.value;
            setValue(e.target.value);
          }}
          onKeyDown={onKey}
          rows={1}
          placeholder={isListening ? "Listening..." : "Ask AUDITO AI anything..."}
          className={cn(
            "min-h-[36px] flex-1 resize-none bg-transparent px-1 py-2 text-sm leading-6 outline-none placeholder:text-muted-foreground",
          )}
        />
        {micSupported ? (
          <Button
            variant={isListening ? "default" : "ghost"}
            size="icon"
            className={cn("h-9 w-9 shrink-0 rounded-full", isListening && "animate-pulse")}
            onClick={onMicClick}
            aria-label={isListening ? "Stop voice input" : "Speak your question"}
          >
            {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 shrink-0 rounded-full"
            disabled
            aria-label="Voice input not supported in this browser"
          >
            <Mic className="h-4 w-4" />
          </Button>
        )}

        {isStreaming ? (
          <Button
            size="icon"
            variant="default"
            className="h-9 w-9 shrink-0 rounded-full"
            onClick={stopGeneration}
            aria-label="Stop generating"
          >
            <Square className="h-3.5 w-3.5" fill="currentColor" />
          </Button>
        ) : (
          <motion.button
            whileTap={{ scale: 0.9 }}
            disabled={!canSend}
            onClick={submit}
            aria-label="Send"
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-colors",
              canSend
                ? "bg-primary text-primary-foreground hover:opacity-90"
                : "cursor-not-allowed bg-muted text-muted-foreground",
            )}
          >
            <ArrowUp className="h-4 w-4" />
          </motion.button>
        )}
      </div>
    </div>
  );
}

