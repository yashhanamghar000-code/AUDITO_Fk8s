import { createFileRoute } from "@tanstack/react-router";
import { ChatArea } from "@/components/chat/ChatArea";

export const Route = createFileRoute("/_authenticated/chat")({
  component: ChatArea,
});
