import { useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { FileText, MessageSquare, ArrowRight } from "lucide-react";
import { AuditoLogo } from "@/components/brand/AuditoLogo";
import { useAuth } from "@/contexts/AuthContext";

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 5) return "Working late";
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  if (hour < 21) return "Good evening";
  return "Working late";
}

const FEATURES = [
  {
    key: "summarize",
    to: "/summarize" as const,
    icon: FileText,
    title: "Summary of PDF Insights",
    description:
      "Upload a report and get a clean, structured summary — key highlights, figures, and risks — in seconds.",
  },
  {
    key: "chat",
    to: "/chat" as const,
    icon: MessageSquare,
    title: "Chat with PDF",
    description:
      "Ask questions about your documents and get grounded, cited answers pulled directly from the source.",
  },
];

export function HomeHub() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const firstName = user?.name?.split(" ")[0];

  return (
    <div className="flex h-full flex-col items-center justify-center px-4 pb-24">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="flex flex-col items-center text-center"
      >
        <AuditoLogo className="h-16 w-16" />
        <h1 className="mt-5 text-2xl font-semibold tracking-tight md:text-3xl">
          {getGreeting()}
          {firstName ? `, ${firstName}` : ""}
        </h1>
        <p className="mt-2 text-sm text-muted-foreground md:text-base">
          What would you like to do today?
        </p>
      </motion.div>

      <div className="mt-10 grid w-full max-w-3xl gap-5 sm:grid-cols-2">
        {FEATURES.map((f, i) => {
          const Icon = f.icon;
          return (
            <motion.button
              key={f.key}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.08 * i }}
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate({ to: f.to })}
              className="group flex flex-col items-start rounded-2xl border border-border bg-card p-6 text-left shadow-sm transition-colors hover:border-foreground/30 hover:bg-accent/40"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-foreground text-background">
                <Icon className="h-5 w-5" />
              </div>
              <h2 className="mt-4 text-base font-semibold tracking-tight">{f.title}</h2>
              <p className="mt-1.5 text-sm text-muted-foreground">{f.description}</p>
              <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-foreground">
                Get started
                <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
              </span>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
