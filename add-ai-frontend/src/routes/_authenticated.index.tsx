import { createFileRoute } from "@tanstack/react-router";
import { HomeHub } from "@/components/home/HomeHub";

export const Route = createFileRoute("/_authenticated/")({
  component: HomeHub,
});
