import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { getSupabase } from "@/lib/supabase";

type Params = { params: Promise<{ id: string }> };

function getAuthFromRequest(req: Request): { user_id: string | null; anonymous_id: string | null } {
  const { searchParams } = new URL(req.url);
  const user_id = searchParams.get("user_id");
  const anonymous_id = searchParams.get("anonymous_id");
  return { user_id, anonymous_id };
}

async function resolveUserId(supabase: ReturnType<typeof getSupabase>): Promise<string | null> {
  if (!supabase) return null;
  const clerkUserId = await auth().then((a) => a.userId ?? null);
  if (!clerkUserId) return null;
  const { data } = await supabase
    .from("users")
    .select("id")
    .eq("clerk_user_id", clerkUserId)
    .limit(1)
    .single();
  return data?.id ?? null;
}

/**
 * GET /api/threads/[id]
 * Load thread and messages. Query: user_id=... or anonymous_id=...
 * If no query, uses Clerk to resolve user_id.
 */
export async function GET(req: Request, { params }: Params) {
  const { id } = await params;
  const supabase = getSupabase();
  if (!supabase) {
    return NextResponse.json(
      { error: "Persistence not configured" },
      { status: 503 }
    );
  }

  let { user_id, anonymous_id } = getAuthFromRequest(req);
  if (!user_id && !anonymous_id) {
    user_id = await resolveUserId(supabase);
  }
  if (!user_id && !anonymous_id) {
    return NextResponse.json(
      { error: "user_id or anonymous_id required" },
      { status: 400 }
    );
  }

  const { data: thread, error: threadError } = await supabase
    .from("chat_threads")
    .select("id, title, bundle_id, user_id, anonymous_id")
    .eq("id", id)
    .single();

  if (threadError || !thread) {
    return NextResponse.json({ error: "Thread not found" }, { status: 404 });
  }

  if (thread.user_id) {
    if (user_id !== thread.user_id) {
      return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
    }
  } else if (thread.anonymous_id) {
    if (anonymous_id !== thread.anonymous_id) {
      return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
    }
  } else {
    return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
  }

  const { data: messages } = await supabase
    .from("chat_messages")
    .select("id, role, content, adaptive_card")
    .eq("thread_id", id)
    .order("created_at", { ascending: true });

  let has_completed_order = false;
  if (thread.bundle_id) {
    const { data: order } = await supabase
      .from("orders")
      .select("id")
      .eq("bundle_id", thread.bundle_id)
      .limit(1)
      .maybeSingle();
    has_completed_order = !!order;
  }

  const latest_order = null; // optional: can be filled from orders if needed

  return NextResponse.json({
    thread: {
      id: thread.id,
      title: thread.title,
      bundle_id: thread.bundle_id,
      has_completed_order,
      latest_order,
    },
    messages: (messages ?? []).map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      adaptiveCard: m.adaptive_card,
    })),
    pending_approvals: [],
  });
}

/**
 * DELETE /api/threads/[id]
 * Delete thread and its messages. Allowed only if the conversation has not ended in an order
 * (no order exists for this thread's bundle). Query: user_id=... or anonymous_id=...
 */
export async function DELETE(req: Request, { params }: Params) {
  const { id } = await params;
  const supabase = getSupabase();
  if (!supabase) {
    return NextResponse.json(
      { error: "Persistence not configured" },
      { status: 503 }
    );
  }

  let { user_id, anonymous_id } = getAuthFromRequest(req);
  if (!user_id && !anonymous_id) {
    user_id = await resolveUserId(supabase);
  }
  if (!user_id && !anonymous_id) {
    return NextResponse.json(
      { error: "user_id or anonymous_id required" },
      { status: 400 }
    );
  }

  const { data: thread, error: threadError } = await supabase
    .from("chat_threads")
    .select("id, bundle_id, user_id, anonymous_id")
    .eq("id", id)
    .single();

  if (threadError || !thread) {
    return NextResponse.json({ error: "Thread not found" }, { status: 404 });
  }

  if (thread.user_id) {
    if (user_id !== thread.user_id) {
      return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
    }
  } else if (thread.anonymous_id) {
    if (anonymous_id !== thread.anonymous_id) {
      return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
    }
  } else {
    return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
  }

  if (thread.bundle_id) {
    const { data: order } = await supabase
      .from("orders")
      .select("id")
      .eq("bundle_id", thread.bundle_id)
      .limit(1)
      .maybeSingle();
    if (order) {
      return NextResponse.json(
        { error: "Cannot delete a conversation that has an order. It is kept for your records." },
        { status: 409 }
      );
    }
  }

  const { error: delError } = await supabase
    .from("chat_threads")
    .delete()
    .eq("id", id);

  if (delError) {
    return NextResponse.json(
      { error: delError.message },
      { status: 500 }
    );
  }

  return NextResponse.json({ ok: true });
}
