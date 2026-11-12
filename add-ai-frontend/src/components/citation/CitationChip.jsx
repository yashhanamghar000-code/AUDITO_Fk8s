/**
 * src/components/citation/CitationChip.jsx
 *
 * Small clickable numbered citation pill, Perplexity-style ("1  report.pdf
 * · p.4"). Clicking it opens the CitationPdfPanel via useCitationViewer().
 * Pure presentation — all "what happens on click" logic lives in the
 * useCitationViewer hook, this component only renders + delegates.
 */
import React from "react";
import { FileText } from "lucide-react";
import { useCitationViewer } from "../../hooks/useCitationViewer";

export default function CitationChip({ citation, index }) {
  const { open } = useCitationViewer();

  if (!citation) return null;

  const page = citation.page ?? "?";

  return (
    <button
      type="button"
      onClick={() => open(citation)}
      title={`Open ${citation.source ?? "document"}, page ${page}`}
      className="group inline-flex max-w-[220px] items-center gap-1.5 rounded-full border border-border bg-muted/60 px-2.5 py-1 text-xs text-foreground/80 transition-colors hover:border-primary/40 hover:bg-primary/10 hover:text-foreground"
    >
      {typeof index === "number" ? (
        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-foreground/10 text-[10px] font-semibold text-foreground/70 group-hover:bg-primary/20 group-hover:text-primary">
          {index}
        </span>
      ) : (
        <FileText className="h-3 w-3 shrink-0" />
      )}
      <span className="truncate">{citation.source ?? "Document"}</span>
      <span className="shrink-0 text-foreground/50">· p.{page}</span>
    </button>
  );
}
