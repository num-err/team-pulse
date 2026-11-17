"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, type Me, type Workspace } from "@/lib/api";
import { DEMO_MODE } from "@/lib/demo";
import { getSupabase, supabaseConfigured } from "@/lib/supabase";

const LAST_WORKSPACE_KEY = "teampulse.workspace";

const DEMO_WORKSPACE: Workspace = {
  id: "demo",
  name: "Acme Inc.",
  timezone: "America/New_York",
  digest_hour: 9,
  digest_minute: 0,
  role: "owner",
};

type SessionState =
  | { status: "loading" }
  | { status: "error"; error: string }
  | { status: "ready"; me: Me; workspace: Workspace | null };

interface SessionValue {
  state: SessionState;
  selectWorkspace: (id: string) => void;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionValue | null>(null);

function readLastWorkspace(): string | null {
  try {
    return localStorage.getItem(LAST_WORKSPACE_KEY);
  } catch {
    return null;
  }
}

function writeLastWorkspace(id: string) {
  try {
    localStorage.setItem(LAST_WORKSPACE_KEY, id);
  } catch {
    /* private mode etc. — selection just won't be remembered */
  }
}

/**
 * Loads the signed-in user and their workspaces. Redirects to /login when
 * signed out. In demo mode, provides a fixed sample workspace instead.
 */
export function SessionProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<SessionState>({ status: "loading" });

  const load = useCallback(async () => {
    if (DEMO_MODE) {
      setState({
        status: "ready",
        me: { user: { id: "demo", email: null }, workspaces: [DEMO_WORKSPACE] },
        workspace: DEMO_WORKSPACE,
      });
      return;
    }
    if (!supabaseConfigured()) {
      setState({ status: "error", error: "Sign-in isn't configured (missing Supabase URL / anon key)." });
      return;
    }
    const { data } = await getSupabase().auth.getSession();
    if (!data.session) {
      router.replace("/login");
      return;
    }
    const result = await api<Me>("/me");
    if (!result.ok) {
      if (result.status === 401) {
        router.replace("/login");
        return;
      }
      setState({ status: "error", error: result.error });
      return;
    }
    const me = result.data;
    const remembered = readLastWorkspace();
    const workspace = me.workspaces.find((w) => w.id === remembered) ?? me.workspaces[0] ?? null;
    setState({ status: "ready", me, workspace });
  }, [router]);

  useEffect(() => {
    load();
    if (DEMO_MODE || !supabaseConfigured()) return;
    const { data } = getSupabase().auth.onAuthStateChange((event) => {
      if (event === "SIGNED_OUT") router.replace("/login");
    });
    return () => data.subscription.unsubscribe();
  }, [load, router]);

  const selectWorkspace = useCallback((id: string) => {
    setState((prev) => {
      if (prev.status !== "ready") return prev;
      const workspace = prev.me.workspaces.find((w) => w.id === id) ?? prev.workspace;
      if (workspace) writeLastWorkspace(workspace.id);
      return { ...prev, workspace };
    });
  }, []);

  const signOut = useCallback(async () => {
    if (DEMO_MODE) return;
    await getSupabase().auth.signOut();
  }, []);

  return (
    <SessionContext.Provider value={{ state, selectWorkspace, refresh: load, signOut }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside <SessionProvider>");
  return value;
}
