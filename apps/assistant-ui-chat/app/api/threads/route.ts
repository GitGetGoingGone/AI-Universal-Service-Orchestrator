import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

/**
 * GET /api/threads
 * List conversation threads. Query: ?anonymous_id=... (required; no Clerk in assistant-ui-chat).
 * Returns threads with has_completed_order when the thread's bundle has an order.
 */
export async function GET(req: Request) {
  const supabase = getSupabase();
  if (!supabase) {
    return NextResponse.json(
      { error: "Persistence not configured" },
      { status: 503 }
    );
  }

  const { searchParams } = new URL(req.url);
  const anonymousId = searchParams.get("anonymous_id");

  if (!anonymousId) {
    return NextResponse.json(
      { error: "anonymous_id required" },
      { status: 400 }
    );
  }

  const { data: threads, error } = await supabase
    .from("chat_threads")
    .select("id, title, updated_at, bundle_id")
    .eq("anonymous_id", anonymousId)
    .order("updated_at", { ascending: false });

  if (error) {
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }

  const list = threads ?? [];
  const bundleIds = list.map((t) => t.bundle_id).filter(Boolean) as string[];

  let hasOrderByBundle: Record<string, boolean> = {};
  if (bundleIds.length > 0) {
    const { data: orders } = await supabase
      .from("orders")
      .select("bundle_id")
      .in("bundle_id", bundleIds);
    hasOrderByBundle = (orders ?? []).reduce(
      (acc, o) => ({ ...acc, [o.bundle_id as string]: true }),
      {} as Record<string, boolean>
    );
  }

  const threadsWithOrder = list.map((t) => ({
    id: t.id,
    title: t.title || "Chat",
    updated_at: t.updated_at,
    has_completed_order: !!t.bundle_id && !!hasOrderByBundle[t.bundle_id],
  }));

  return NextResponse.json({ threads: threadsWithOrder });
}
