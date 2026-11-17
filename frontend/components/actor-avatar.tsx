"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

// Muted, professional tints for initials avatars (bg + text).
const TINTS = [
  "bg-indigo-100 text-indigo-700",
  "bg-sky-100 text-sky-700",
  "bg-emerald-100 text-emerald-700",
  "bg-amber-100 text-amber-800",
  "bg-rose-100 text-rose-700",
  "bg-violet-100 text-violet-700",
];

function tintFor(name: string) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return TINTS[Math.abs(hash) % TINTS.length];
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function ActorAvatar({ actor, className }: { actor: string; className?: string }) {
  const [imgFailed, setImgFailed] = useState(false);
  const looksLikeGithubLogin = /^[a-zA-Z0-9-]+$/.test(actor);

  if (!imgFailed && looksLikeGithubLogin) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={`https://github.com/${actor}.png?size=64`}
        alt={actor}
        onError={() => setImgFailed(true)}
        className={cn("h-9 w-9 rounded-full object-cover ring-1 ring-border", className)}
      />
    );
  }

  return (
    <div
      aria-hidden
      className={cn(
        "flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
        tintFor(actor),
        className
      )}
    >
      {initials(actor)}
    </div>
  );
}
