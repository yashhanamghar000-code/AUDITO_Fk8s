import { createFileRoute } from "@tanstack/react-router";
import { SummarizeArea } from "@/components/summarize/SummarizeArea";

export const Route = createFileRoute("/_authenticated/summarize")({
  component: SummarizeArea,
});
