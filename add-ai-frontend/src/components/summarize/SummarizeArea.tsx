import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Sparkles, Copy, Check, RefreshCw } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { UploadCard } from "@/components/upload/UploadCard";
import { useChat } from "@/contexts/ChatContext";
import { summarizeService } from "@/services/summarize";
import { ThinkingIndicator, SUMMARY_PHASES } from "@/components/chat/ThinkingIndicator";
import { cn } from "@/lib/utils";

export function SummarizeArea() {
  const { documents } = useChat();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const indexedDocs = useMemo(
    () => documents.filter((d) => d.status === "indexed"),
    [documents],
  );
  const activeId = selectedId ?? indexedDocs[0]?.id ?? null;

  async function generateSummary() {
    if (!activeId) return;
    setLoading(true);
    setSummary(null);
    try {
      const res = await summarizeService.summarize(activeId);
      setSummary(res.data.summary);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? "Couldn't generate a summary for this document.");
    } finally {
      setLoading(false);
    }
  }

  async function copySummary() {
    if (!summary) return;
    await navigator.clipboard.writeText(summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Summary of PDF Insights</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Pick a document and get a structured summary of its key points.
          </p>
        </div>

        {indexedDocs.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border p-8">
            <UploadCard />
            <p className="mt-3 text-center text-xs text-muted-foreground">
              Upload a PDF above — once it's indexed, you can summarize it here.
            </p>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap gap-2">
              {indexedDocs.map((d) => (
                <button
                  key={d.id}
                  onClick={() => {
                    setSelectedId(d.id);
                    setSummary(null);
                  }}
                  className={cn(
                    "flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors",
                    activeId === d.id
                      ? "border-foreground bg-foreground text-background"
                      : "border-border text-foreground/80 hover:border-foreground/40 hover:bg-accent",
                  )}
                >
                  <FileText className="h-3.5 w-3.5" />
                  <span className="max-w-[180px] truncate">{d.name}</span>
                </button>
              ))}
            </div>

            <Button
              onClick={generateSummary}
              disabled={!activeId || loading}
              className="w-full gap-2 sm:w-fit"
              size="lg"
            >
              {loading ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Generating summary…
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  {summary ? "Regenerate summary" : "Generate summary"}
                </>
              )}
            </Button>

            <AnimatePresence mode="wait">
              {loading && (
                <motion.div
                  key="skeleton"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-4 rounded-2xl border border-border bg-card p-6"
                >
                  <ThinkingIndicator phases={SUMMARY_PHASES} />
                  {[0, 1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-3 animate-pulse rounded-full bg-muted"
                      style={{ width: `${90 - i * 10}%` }}
                    />
                  ))}
                </motion.div>
              )}

              {!loading && summary && (
                <motion.div
                  key="summary"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="relative rounded-2xl border border-border bg-card p-6"
                >
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-3 top-3 h-7 w-7"
                    onClick={copySummary}
                    aria-label="Copy summary"
                  >
                    {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                  </Button>
                  <div className="prose-chat text-sm">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{summary}</ReactMarkdown>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </div>
    </div>
  );
}
