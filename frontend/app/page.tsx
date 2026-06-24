import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-24 text-center">
      <h1 className="text-4xl font-bold tracking-tight">Team Pulse</h1>
      <p className="max-w-md text-muted-foreground">
        Zero-input async standups. We pull the signal from where your team
        already works — no forms to fill out.
      </p>
      <Button asChild>
        <Link href="/dashboard">Go to dashboard</Link>
      </Button>
    </main>
  );
}
