"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

const GRADIENTS = [
  "from-violet-500 to-fuchsia-500",
  "from-sky-500 to-cyan-400",
  "from-emerald-500 to-teal-400",
  "from-orange-500 to-amber-400",
  "from-pink-500 to-rose-400",
];

function gradientFor(name: string) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return GRADIENTS[Math.abs(hash) % GRADIENTS.length];
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
        className={cn("h-9 w-9 rounded-full border border-white/10 object-cover", className)}
      />
    );
  }

  return (
    <div
      className={cn(
        "flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br text-xs font-semibold text-white",
        gradientFor(actor),
        className
      )}
    >
      {initials(actor)}
    </div>
  );
}
