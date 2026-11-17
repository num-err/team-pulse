"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Github, Mail, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/logo";
import { DEMO_MODE } from "@/lib/demo";
import { appUrl, getSupabase, supabaseConfigured } from "@/lib/supabase";

type Status = { kind: "idle" } | { kind: "sending" } | { kind: "sent"; email: string } | { kind: "error"; message: string };

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  useEffect(() => {
    if (DEMO_MODE) {
      router.replace("/dashboard");
      return;
    }
    if (!supabaseConfigured()) return;
    getSupabase()
      .auth.getSession()
      .then(({ data }) => {
        if (data.session) router.replace("/dashboard");
      });
  }, [router]);

  async function sendMagicLink(e: React.FormEvent) {
    e.preventDefault();
    const address = email.trim();
    if (!address) return;
    setStatus({ kind: "sending" });
    const { error } = await getSupabase().auth.signInWithOtp({
      email: address,
      options: { emailRedirectTo: appUrl("/dashboard") },
    });
    setStatus(error ? { kind: "error", message: error.message } : { kind: "sent", email: address });
  }

  async function signInWith(provider: "github" | "google") {
    const { error } = await getSupabase().auth.signInWithOAuth({
      provider,
      options: { redirectTo: appUrl("/dashboard") },
    });
    if (error) setStatus({ kind: "error", message: error.message });
  }

  const configured = supabaseConfigured();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12">
      <Link href="/" className="mb-8" aria-label="Team Pulse home">
        <Logo />
      </Link>

      <div className="w-full max-w-sm rounded-xl border bg-card p-6 shadow-card sm:p-8">
        {status.kind === "sent" ? (
          <div className="text-center">
            <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-accent text-primary">
              <Mail className="h-5 w-5" />
            </div>
            <h1 className="mt-4 text-lg font-semibold">Check your email</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              We sent a sign-in link to <span className="font-medium text-foreground">{status.email}</span>. Open it in
              this browser to continue.
            </p>
            <Button variant="ghost" className="mt-5" onClick={() => setStatus({ kind: "idle" })}>
              <ArrowLeft className="h-4 w-4" /> Use a different email
            </Button>
          </div>
        ) : (
          <>
            <h1 className="text-lg font-semibold">Sign in to Team Pulse</h1>
            <p className="mt-1 text-sm text-muted-foreground">Use your work email. New here? Signing in creates your account.</p>

            {!configured && (
              <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                Sign-in isn&apos;t configured for this build.
              </p>
            )}

            <div className="mt-6 space-y-2">
              <Button variant="outline" className="w-full" onClick={() => signInWith("google")} disabled={!configured}>
                <GoogleMark /> Continue with Google
              </Button>
              <Button variant="outline" className="w-full" onClick={() => signInWith("github")} disabled={!configured}>
                <Github className="h-4 w-4" /> Continue with GitHub
              </Button>
            </div>

            <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
              <span className="h-px flex-1 bg-border" /> or <span className="h-px flex-1 bg-border" />
            </div>

            <form onSubmit={sendMagicLink} className="space-y-3">
              <label className="block">
                <span className="text-sm font-medium">Work email</span>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1.5 h-9 w-full rounded-md border border-input bg-card px-3 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                />
              </label>
              <Button type="submit" className="w-full" disabled={!configured || status.kind === "sending"}>
                {status.kind === "sending" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
                Email me a sign-in link
              </Button>
            </form>

            {status.kind === "error" && <p className="mt-3 text-sm text-red-600">{status.message}</p>}
          </>
        )}
      </div>

      <p className="mt-6 text-xs text-muted-foreground">
        Just looking?{" "}
        <a href="https://num-err.github.io/team-pulse/dashboard/" className="font-medium text-primary hover:underline">
          Try the demo with sample data
        </a>
      </p>
    </main>
  );
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
      <path fill="#4285F4" d="M23.5 12.27c0-.85-.08-1.67-.22-2.45H12v4.64h6.45a5.52 5.52 0 0 1-2.4 3.62v3h3.88c2.27-2.09 3.57-5.17 3.57-8.81z" />
      <path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.95-2.92l-3.88-3c-1.08.72-2.45 1.15-4.07 1.15-3.13 0-5.78-2.11-6.73-4.95H1.27v3.1A12 12 0 0 0 12 24z" />
      <path fill="#FBBC05" d="M5.27 14.28A7.2 7.2 0 0 1 4.9 12c0-.79.14-1.56.37-2.28v-3.1H1.27A12 12 0 0 0 0 12c0 1.94.46 3.77 1.27 5.38l4-3.1z" />
      <path fill="#EA4335" d="M12 4.77c1.76 0 3.35.61 4.6 1.8l3.44-3.44A11.97 11.97 0 0 0 12 0 12 12 0 0 0 1.27 6.62l4 3.1C6.22 6.88 8.87 4.77 12 4.77z" />
    </svg>
  );
}
