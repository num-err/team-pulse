import { DEMO_MODE, demoPost } from "@/lib/demo";
import { getSupabase } from "@/lib/supabase";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string; status?: number };

export interface Workspace {
  id: string;
  name: string;
  timezone: string;
  digest_hour: number;
  digest_minute: number;
  role: "owner" | "admin" | "member";
}

export interface Me {
  user: { id: string; email: string | null };
  workspaces: Workspace[];
}

export interface Integration {
  provider: "github" | "linear" | "figma" | "notion" | "slack";
  connected: boolean;
  settings: Record<string, unknown>;
  updated_at: string | null;
  webhook_url?: string;
}

/**
 * Call the backend as the signed-in user. Sends the Supabase access token
 * as a Bearer token; a 401 means the session is gone, so we send the user
 * back to sign in.
 */
export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<ApiResult<T>> {
  const method = init.method ?? "GET";
  if (DEMO_MODE) {
    return (await demoPost(path)) as ApiResult<T>;
  }

  const { data } = await getSupabase().auth.getSession();
  const token = data.session?.access_token;
  if (!token) return { ok: false, error: "Not signed in.", status: 401 };

  try {
    const res = await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(init.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    });
    if (res.status === 204) return { ok: true, data: undefined as T };
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = Array.isArray(body.detail) ? body.detail.map((d: { msg: string }) => d.msg).join("; ") : body.detail;
      return { ok: false, error: detail ?? `Error ${res.status}`, status: res.status };
    }
    return { ok: true, data: body as T };
  } catch {
    return { ok: false, error: "Could not reach the API." };
  }
}

/** Path to a workspace-scoped endpoint, e.g. ws(id, "/digest/team"). */
export function ws(workspaceId: string, path: string): string {
  return `/workspaces/${workspaceId}${path}`;
}
