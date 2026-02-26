import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

type Params = { params: Promise<{ id: string }> };

/**
 * GET /api/threads/[id]
 * Load thread and messages. Query: ?anonymous_id=...
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

  const { searchParams } = new URL(req.url);
  const anonymousId = searchParams.get("anonymous_id");

  if (!anonymousId) {
    return NextResponse.json(
      { error: "anonymous_id required" },
      { status: 400 }
    );
  }

  const { data: thread, error: threadError } = await supabase
    .from("chat_threads")
    .select("id, title, bundle_id, anonymous_id")
    .eq("id", id)
    .single();

  if (threadError || !thread) {
    return NextResponse.json({ error: "Thread not found" }, { status: 404 });
  }

  if (thread.anonymous_id !== anonymousId) {
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

  return NextResponse.json({
    thread: {
      id: thread.id,
      title: thread.title,
      bundle_id: thread.bundle_id,
      has_completed_order,
    },
    messages: (messages ?? []).map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      adaptiveCard: m.adaptive_card,
    })),
  });
}

/**
 * DELETE /api/threads/[id]
 * Delete thread and its messages. Allowed only if the thread has no completed order.
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

  const { searchParams } = new URL(req.url);
  const anonymousId = searchParams.get("anonymous_id");

  if (!anonymousId) {
    return NextResponse.json(
      { error: "anonymous_id required" },
      { status: 400 }
    );
  }

  const { data: thread, error: threadError } = await supabase
    .from("chat_threads")
    .select("id, bundle_id, anonymous_id")
    .eq("id", id)
    .single();

  if (threadError || !thread) {
    return NextResponse.json({ error: "Thread not found" }, { status: 404 });
  }

  if (thread.anonymous_id !== anonymousId) {
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
