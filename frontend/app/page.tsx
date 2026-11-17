import Link from "next/link";
import {
  ArrowRight,
  BrainCircuit,
  Clock,
  Fingerprint,
  Github,
  Hash,
  Layers,
  Plug,
  RefreshCcw,
  ShieldCheck,
  Send,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo, LogoMark } from "@/components/logo";
import { IntegrationsStrip } from "@/components/integrations-strip";
import { HealthBadge, HEALTH_META, type HealthState } from "@/components/health-badge";
import { DEMO_MODE } from "@/lib/demo";

const REPO_URL = "https://github.com/num-err/team-pulse";

const STEPS: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: Plug,
    title: "Connect the tools you already use",
    body: "Signed webhooks from GitHub and Linear, API polling for Notion, and Figma comments. No forms for anyone to fill in.",
  },
  {
    icon: BrainCircuit,
    title: "Summarize each person's day",
    body: "Claude turns raw commits, PRs, tickets and doc edits into a short, specific standup for every contributor.",
  },
  {
    icon: Send,
    title: "Deliver it before standup",
    body: "A team rollup lands in Slack every morning, with anyone who needs a check-in called out at the end.",
  },
];

const SIGNAL_ORDER: HealthState[] = ["HEALTHY", "THRASHING", "SILENT_STUCK", "IDLE"];

const ENGINEERING: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: ShieldCheck,
    title: "Verified ingestion",
    body: "HMAC-SHA256 signature checks on every webhook; production refuses to boot with missing secrets.",
  },
  {
    icon: RefreshCcw,
    title: "Idempotent by design",
    body: "Per-source dedup keys and a unique constraint make retried webhook deliveries harmless.",
  },
  {
    icon: Fingerprint,
    title: "Identity resolution",
    body: "One person, many handles: aliases map GitHub, Linear and Notion identities to a single teammate.",
  },
  {
    icon: Clock,
    title: "Restart-safe scheduling",
    body: "Job runs are persisted, so a restart past 9am catches up once — never double-posts to Slack.",
  },
  {
    icon: Layers,
    title: "Graceful failure",
    body: "Transient AI errors retry, permanent ones fail fast, and one person's failure never blocks the team digest.",
  },
  {
    icon: BrainCircuit,
    title: "Precision over recall",
    body: "Health flags need an independent struggle signal, not just volume — a false alarm costs more than a miss.",
  },
];

const STACK = ["FastAPI", "Python 3.13", "PostgreSQL", "Claude Haiku", "Slack SDK", "APScheduler", "Next.js", "TypeScript"];

export default function Home() {
  return (
    <div className="min-h-screen bg-card">
      {/* Nav */}
      <header className="sticky top-0 z-20 border-b bg-card/90 backdrop-blur supports-[backdrop-filter]:bg-card/75">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" aria-label="Team Pulse home">
            <Logo />
          </Link>
          <nav className="flex items-center gap-1 sm:gap-2">
            <a href="#how" className="hidden rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-foreground md:inline">
              How it works
            </a>
            <a
              href="#signals"
              className="hidden rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-foreground md:inline"
            >
              Health signals
            </a>
            <a
              href="#engineering"
              className="hidden rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-foreground md:inline"
            >
              Engineering
            </a>
            <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
              <a href={REPO_URL} target="_blank" rel="noreferrer">
                <Github className="h-4 w-4" /> GitHub
              </a>
            </Button>
            {!DEMO_MODE && (
              <Button asChild variant="ghost" size="sm">
                <Link href="/login">Sign in</Link>
              </Button>
            )}
            <Button asChild size="sm">
              <Link href="/dashboard">
                View live demo <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b bg-background">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 sm:py-20 lg:grid-cols-[1.05fr_1fr] lg:gap-16 lg:py-24">
          <div>
            <p className="text-sm font-semibold text-primary">Async standups for product teams</p>
            <h1 className="mt-3 text-4xl font-semibold leading-[1.1] tracking-tight text-foreground sm:text-5xl">
              Your team&apos;s standup, written from the work they already did.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-muted-foreground">
              Team Pulse reads activity from GitHub, Linear, Notion and Figma, writes each person&apos;s daily update
              with AI, and posts it to Slack — then flags anyone who looks stuck before they say so.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Button asChild size="lg">
                <Link href="/dashboard">
                  View live demo <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <a href={REPO_URL} target="_blank" rel="noreferrer">
                  <Github className="h-4 w-4" /> View source
                </a>
              </Button>
            </div>
            <div className="mt-10 border-t pt-6">
              <p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">Works with</p>
              <IntegrationsStrip />
            </div>
          </div>

          <SlackPreview />
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="scroll-mt-16 border-b">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <SectionIntro
            eyebrow="How it works"
            title="Zero input from your team"
            body="Nobody fills in a form or answers a bot at 9am. The standup is built from signals your tools already produce."
          />
          <ol className="mt-12 grid gap-6 md:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, body }, i) => (
              <li key={title} className="rounded-lg border bg-card p-6 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="flex h-10 w-10 items-center justify-center rounded-md bg-accent text-primary">
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="text-sm font-medium text-muted-foreground tabular">0{i + 1}</span>
                </div>
                <h3 className="mt-5 font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Health signals */}
      <section id="signals" className="scroll-mt-16 border-b bg-background">
        <div className="mx-auto grid max-w-6xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_1.4fr] lg:gap-16">
          <SectionIntro
            eyebrow="Health signals"
            title="Spot who's stuck before they say so"
            body="Every person is classified from their last three days of activity. Concerning states are surfaced on the dashboard and at the bottom of the Slack digest — framed as a question, not a verdict."
          />
          <div className="grid gap-4 sm:grid-cols-2">
            {SIGNAL_ORDER.map((state) => (
              <div key={state} className="rounded-lg border bg-card p-5 shadow-xs">
                <HealthBadge state={state} />
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{HEALTH_META[state].description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Engineering */}
      <section id="engineering" className="scroll-mt-16 border-b">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <SectionIntro
            eyebrow="Engineering"
            title="Built like a production service"
            body="A FastAPI backend on Postgres with a scheduled AI pipeline — designed around the failure modes of real webhook traffic."
          />
          <div className="mt-12 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {ENGINEERING.map(({ icon: Icon, title, body }) => (
              <div key={title} className="flex gap-4">
                <Icon className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                <div>
                  <h3 className="font-semibold">{title}</h3>
                  <p className="mt-1.5 text-sm leading-6 text-muted-foreground">{body}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-12 flex flex-wrap gap-2 border-t pt-8">
            {STACK.map((s) => (
              <span key={s} className="rounded-md border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground">
                {s}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-background">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <div className="flex flex-col items-start justify-between gap-6 rounded-xl border bg-card p-8 shadow-card md:flex-row md:items-center md:p-10">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">See it on a sample team</h2>
              <p className="mt-2 max-w-lg text-muted-foreground">
                The demo runs on a four-person team with one engineer quietly struggling. No sign-up required.
              </p>
            </div>
            <Button asChild size="lg">
              <Link href="/dashboard">
                Open the dashboard <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <footer className="border-t bg-card">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-4 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:px-6">
          <span className="inline-flex items-center gap-2">
            <LogoMark className="h-5 w-5" /> Team Pulse · Portfolio project
          </span>
          <a href={REPO_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 hover:text-foreground">
            <Github className="h-4 w-4" /> num-err/team-pulse
          </a>
        </div>
      </footer>
    </div>
  );
}

function SectionIntro({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <div className="max-w-2xl">
      <p className="text-sm font-semibold text-primary">{eyebrow}</p>
      <h2 className="mt-2 text-3xl font-semibold tracking-tight">{title}</h2>
      <p className="mt-4 text-base leading-7 text-muted-foreground">{body}</p>
    </div>
  );
}

/** A faithful mock of the Block Kit message the backend posts to Slack. */
function SlackPreview() {
  return (
    <div className="overflow-hidden rounded-xl border bg-card shadow-card">
      <div className="flex items-center justify-between border-b bg-secondary/60 px-4 py-2.5">
        <span className="inline-flex items-center gap-1.5 text-sm font-semibold">
          <Hash className="h-4 w-4 text-muted-foreground" /> eng-standup
        </span>
        <span className="text-xs text-muted-foreground">Slack</span>
      </div>
      <div className="flex gap-3 p-5">
        <LogoMark className="h-9 w-9 shrink-0" />
        <div className="min-w-0 flex-1 text-sm">
          <p className="flex items-center gap-2">
            <span className="font-semibold">Team Pulse</span>
            <span className="rounded bg-secondary px-1 text-[10px] font-semibold uppercase text-muted-foreground">App</span>
            <span className="text-xs text-muted-foreground">9:00 AM</span>
          </p>
          <p className="mt-2 font-semibold">Team Pulse — Daily digest</p>
          <p className="mt-1.5 leading-6 text-foreground/85">
            The payments push is moving: Marcus merged webhook retry logic, Priya closed out Q3 pricing tiers, and
            Sara&apos;s onboarding v4 is ready for handoff.
          </p>
          <div className="my-3 h-px bg-border" />
          <ul className="space-y-2.5 text-[13px] leading-5">
            <li>
              <span className="font-semibold">Marcus Webb</span>{" "}
              <span className="text-foreground/80">— Added retry logic to the payment webhook handler and fixed a flaky checkout test.</span>
            </li>
            <li>
              <span className="font-semibold">Priya Sharma</span>{" "}
              <span className="text-foreground/80">— Updated the Q3 roadmap and published the enterprise interview synthesis.</span>
            </li>
          </ul>
          <div className="mt-3 rounded-md border border-l-4 border-l-amber-500 bg-amber-50/60 px-3 py-2.5 text-[13px] leading-5">
            <p className="font-semibold text-amber-900">⚠ Attention</p>
            <p className="mt-0.5 text-amber-900/80">
              <span className="font-medium">Dev Okoye</span> — 16 commits to acme/pricing-service over 3 days, 0 merges,
              7 CI failures.
            </p>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">4 contributors · 17 events</p>
        </div>
      </div>
    </div>
  );
}
