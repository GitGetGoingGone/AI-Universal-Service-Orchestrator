import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

type MetricsAgg = {
  total_estimated_tokens?: number;
  turn_count?: number;
  last_memory_health?: string | null;
};

function parseMetrics(raw: unknown): { aggregated: MetricsAgg | null; turns_len: number } {
  if (!raw || typeof raw !== "object") return { aggregated: null, turns_len: 0 };
  const m = raw as { aggregated?: MetricsAgg; turns?: unknown[] };
  const turns = Array.isArray(m.turns) ? m.turns : [];
  return {
    aggregated: m.aggregated && typeof m.aggregated === "object" ? m.aggregated : null,
    turns_len: turns.length,
  };
}

export async function GET(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { searchParams } = new URL(request.url);
    const userId = searchParams.get("user_id")?.trim() || null;
    const anonymousId = searchParams.get("anonymous_id")?.trim() || null;
    const from = searchParams.get("from");
    const to = searchParams.get("to");
    const limit = Math.min(200, Math.max(1, Number(searchParams.get("limit")) || 80));

    const supabase = createSupabaseServerClient();
    let q = supabase
      .from("chat_threads")
      .select("id, user_id, anonymous_id, title, bundle_id, created_at, updated_at, conversation_metrics")
      .order("updated_at", { ascending: false })
      .limit(limit);

    if (userId) q = q.eq("user_id", userId);
    if (anonymousId) q = q.eq("anonymous_id", anonymousId);
    if (from) q = q.gte("updated_at", from);
    if (to) q = q.lte("updated_at", to);

    const { data, error } = await q;

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    const rows = (data ?? []).map((row) => {
      const { aggregated, turns_len } = parseMetrics(row.conversation_metrics);
      return {
        id: row.id,
        user_id: row.user_id,
        anonymous_id: row.anonymous_id,
        title: row.title,
        bundle_id: row.bundle_id,
        created_at: row.created_at,
        updated_at: row.updated_at,
        metrics_turns: turns_len,
        estimated_tokens_total: aggregated?.total_estimated_tokens ?? null,
        memory_health_last: aggregated?.last_memory_health ?? null,
        conversation_metrics: row.conversation_metrics,
      };
    });

    const byUser = new Map<string, { thread_count: number; tokens: number }>();
    for (const r of rows) {
      const key = r.user_id || r.anonymous_id || "unknown";
      const cur = byUser.get(key) ?? { thread_count: 0, tokens: 0 };
      cur.thread_count += 1;
      cur.tokens += r.estimated_tokens_total ?? 0;
      byUser.set(key, cur);
    }

    const user_rollups = [...byUser.entries()].map(([key, v]) => ({
      user_key: key,
      thread_count: v.thread_count,
      estimated_tokens_total: v.tokens,
    }));

    return NextResponse.json({ conversations: rows, user_rollups });
  } catch {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
