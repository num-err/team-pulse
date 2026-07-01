"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles, Zap, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { IntegrationsStrip } from "@/components/integrations-strip";

const FEATURES = [
  {
    icon: Zap,
    title: "Zero input",
    description: "No forms, no bot nagging you at 9am. We read the signal your team already produces.",
  },
  {
    icon: Sparkles,
    title: "AI synthesis",
    description: "Claude turns raw commits, PRs, tickets, and docs into a plain-English summary of real work.",
  },
  {
    icon: Users,
    title: "Whole-team pulse",
    description: "One rollup shows what everyone shipped, with per-person detail one click away.",
  },
];

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden">
      <div className="bg-grid pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,black,transparent)]" />

      <div
        aria-hidden
        className="pointer-events-none absolute -top-32 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 animate-float rounded-full bg-violet-600/20 blur-[120px]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute right-0 top-1/3 h-80 w-80 rounded-full bg-sky-500/20 blur-[100px]"
      />

      <nav className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-sky-400 text-sm">
            ⚡
          </span>
          Team Pulse
        </div>
        <Button asChild variant="ghost" size="sm">
          <Link href="/dashboard">
            Dashboard <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
          </Link>
        </Button>
      </nav>

      <section className="relative z-10 mx-auto flex max-w-4xl flex-col items-center gap-8 px-6 pb-24 pt-16 text-center sm:pt-24">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="glass inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs text-muted-foreground"
        >
          <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-success" />
          Live — synthesizing real activity right now
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.05 }}
          className="text-5xl font-bold leading-[1.1] tracking-tight sm:text-6xl"
        >
          Standups that write
          <br />
          <span className="gradient-text">themselves.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="max-w-lg text-balance text-lg text-muted-foreground"
        >
          Team Pulse pulls signal from GitHub, Linear, Notion, and Figma, then
          uses AI to write your team&apos;s daily standup for you — and drops it
          straight into Slack.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
        >
          <Button asChild size="lg" className="group bg-gradient-to-r from-violet-500 to-sky-400 text-white hover:opacity-90">
            <Link href="/dashboard">
              Open live dashboard
              <ArrowRight className="ml-1.5 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Button>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="mt-4 flex flex-col items-center gap-3"
        >
          <span className="text-xs uppercase tracking-widest text-muted-foreground">
            Connected sources
          </span>
          <IntegrationsStrip />
        </motion.div>
      </section>

      <section className="relative z-10 mx-auto grid max-w-5xl gap-4 px-6 pb-24 sm:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, description }, i) => (
          <motion.div
            key={title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
            className="glass glow-border rounded-2xl p-6"
          >
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/20 to-sky-400/20">
              <Icon className="h-5 w-5 text-violet-300" />
            </div>
            <h3 className="mb-1.5 font-semibold">{title}</h3>
            <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
          </motion.div>
        ))}
      </section>
    </main>
  );
}
