import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabase } from "@/lib/supabase";

/**
 * GET /api/threads
 * List conversation threads for the current user (user_id or anonymous_id).
 * Returns threads with has_completed_order: true if the thread's bundle has an order.
 * For signed-in: no query needed (uses Clerk). Query: ?anonymous_id=... for anonymous.
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
  let userId: string | null = searchParams.get("user_id");
  const anonymousId = searchParams.get("anonymous_id");

  if (!userId && !anonymousId) {
    const clerkUserId = await auth().then((a) => a.userId ?? null);
    if (clerkUserId) {
      const { data: user } = await supabase
        .from("users")
        .select("id")
        .eq("clerk_user_id", clerkUserId)
        .limit(1)
        .single();
      userId = user?.id ?? null;
    }
  }

  if (!userId && !anonymousId) {
    return NextResponse.json(
      { error: "user_id or anonymous_id required" },
      { status: 400 }
    );
  }

  let query = supabase
    .from("chat_threads")
    .select("id, title, updated_at, bundle_id")
    .order("updated_at", { ascending: false });

  if (userId) {
    query = query.eq("user_id", userId);
  } else {
    query = query.eq("anonymous_id", anonymousId);
  }

  const { data: threads, error } = await query;

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
      (acc, o) => ({ ...acc, [o.bundle_id]: true }),
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
