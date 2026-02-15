import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabase } from "@/lib/supabase";

/**
 * POST /api/feedback
 * Record like/dislike on a message for analytics and personalization.
 * Body: { thread_id, message_id?, rating: 'like'|'dislike', anonymous_id?, context?: { product_ids?: string[] } }
 */
export async function POST(req: Request) {
  try {
    const supabase = getSupabase();
    if (!supabase) {
      return NextResponse.json(
        { error: "Persistence not configured" },
        { status: 503 }
      );
    }

    const body = await req.json().catch(() => ({}));
    const {
      thread_id,
      message_id,
      rating,
      anonymous_id: reqAnonymousId,
      context = {},
    } = body as {
      thread_id?: string;
      message_id?: string;
      rating?: string;
      anonymous_id?: string;
      context?: { product_ids?: string[] };
    };

    if (!thread_id || !rating) {
      return NextResponse.json(
        { error: "thread_id and rating required" },
        { status: 400 }
      );
    }

    if (rating !== "like" && rating !== "dislike") {
      return NextResponse.json(
        { error: "rating must be 'like' or 'dislike'" },
        { status: 400 }
      );
    }

    let userId: string | null = null;
    let anonymousId: string | null = null;
    try {
      const { userId: clerkUserId } = await auth();
      if (clerkUserId) {
        const { data: user } = await supabase
          .from("users")
          .select("id")
          .eq("clerk_user_id", clerkUserId)
          .limit(1)
          .single();
        userId = user?.id ?? null;
      }
    } catch {
      userId = null;
    }

    const { data: thread } = await supabase
      .from("chat_threads")
      .select("id, user_id, anonymous_id")
      .eq("id", thread_id)
      .single();

    if (!thread) {
      return NextResponse.json({ error: "Thread not found" }, { status: 404 });
    }

    if (thread.user_id) {
      if (userId !== thread.user_id) {
        return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
      }
    } else if (thread.anonymous_id) {
      if (reqAnonymousId && reqAnonymousId !== thread.anonymous_id) {
        return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
      }
      anonymousId = thread.anonymous_id;
    }

    const row: Record<string, unknown> = {
      thread_id,
      rating,
      context: context && typeof context === "object" ? context : {},
    };
    if (message_id) row.message_id = message_id;
    if (userId) row.user_id = userId;
    else if (anonymousId) row.anonymous_id = anonymousId;

    const { error } = await supabase.from("message_feedback").insert(row);

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Failed to record feedback";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
