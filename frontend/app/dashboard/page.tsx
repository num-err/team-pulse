import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const updates = [
  {
    name: "Ava Chen",
    role: "Backend",
    summary:
      "Shipped the standup ingestion worker; investigating a flaky Supabase migration.",
  },
  {
    name: "Marcus Lee",
    role: "Frontend",
    summary:
      "Dashboard layout in review. Next: wire the activity feed to the API.",
  },
  {
    name: "Priya Nair",
    role: "Design",
    summary:
      "Finalized the empty-state illustrations and dark-mode tokens.",
  },
];

export default function DashboardPage() {
  return (
    <main className="container mx-auto max-w-5xl py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Team Pulse</h1>
        <p className="text-muted-foreground">
          Today&apos;s async standup — generated from your team&apos;s activity.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {updates.map((u) => (
          <Card key={u.name}>
            <CardHeader>
              <CardTitle className="text-lg">{u.name}</CardTitle>
              <CardDescription>{u.role}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed">{u.summary}</p>
            </CardContent>
          </Card>
        ))}
      </section>
    </main>
  );
}
