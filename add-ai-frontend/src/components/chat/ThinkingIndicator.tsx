import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Search, FileText, Sparkles, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * One rotating phase of the thinking indicator. Kept as plain data (not
 * JSX) so callers can supply their own phrase sets per surface (chat vs.
 * summarize) without touching this component — Open/Closed: new phrase
 * sets are additions, never edits to ThinkingIndicator itself.
 */
export interface ThinkingPhase {
  icon: LucideIcon;
  label: string;
}

export const DEFAULT_CHAT_PHASES: ThinkingPhase[] = [
  { icon: Search, label: "Searching your documents" },
  { icon: FileText, label: "Reading relevant sections" },
  { icon: Sparkles, label: "Thinking it through" },
  { icon: Sparkles, label: "Drafting an answer" },
];

export const SUMMARY_PHASES: ThinkingPhase[] = [
  { icon: FileText, label: "Scanning the document" },
  { icon: Search, label: "Pulling out key sections" },
  { icon: Sparkles, label: "Writing the summary" },
];

interface ThinkingIndicatorProps {
  /** Ordered phases to cycle through. Defaults to the chat phrase set. */
  phases?: ThinkingPhase[];
  /** Milliseconds each phase stays on screen before advancing. */
  intervalMs?: number;
  className?: string;
}

/**
 * Perplexity-style loading state: a small pulsing icon paired with
 * rotating status text ("Searching your documents" -> "Reading relevant
 * sections" -> ...). Purely presentational and self-contained — it owns
 * its own timer and has no knowledge of *why* the caller is loading.
 */
export function ThinkingIndicator({
  phases = DEFAULT_CHAT_PHASES,
  intervalMs = 1800,
  className,
}: ThinkingIndicatorProps) {
  const [index, setIndex] = useState(0);
  const phasesRef = useRef(phases);
  phasesRef.current = phases;

  useEffect(() => {
    setIndex(0);
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % phasesRef.current.length);
    }, intervalMs);
    return () => clearInterval(id);
  }, [phases, intervalMs]);

  const phase = phases[index] ?? phases[0];
  const Icon = phase.icon;

  return (
    <div className={cn("flex items-center gap-2 py-1", className)}>
      <motion.span
        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary"
        animate={{ scale: [1, 1.12, 1], opacity: [0.75, 1, 0.75] }}
        transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
      >
        <Icon className="h-3 w-3" />
      </motion.span>

      <AnimatePresence mode="wait">
        <motion.span
          key={phase.label}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.25 }}
          className="text-sm text-muted-foreground"
        >
          {phase.label}
          <motion.span
            aria-hidden
            animate={{ opacity: [0, 1, 0] }}
            transition={{ duration: 1.2, repeat: Infinity }}
          >
            …
          </motion.span>
        </motion.span>
      </AnimatePresence>
    </div>
  );
}
