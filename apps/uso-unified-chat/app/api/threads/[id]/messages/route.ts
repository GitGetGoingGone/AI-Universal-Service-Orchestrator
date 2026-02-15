import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

/**
 * Append messages to a thread. Used for action-based messages (add to bundle,
 * checkout, payment confirmation) that are not persisted via the chat API.
 * Body: { messages: [{ role, content?, adaptive_card? }] }
 */
export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const supabase = getSupabase();
  if (!supabase) {
    return NextResponse.json(
      { error: "Persistence not configured" },
      { status: 503 }
    );
  }

  const body = await req.json().catch(() => ({}));
  const { messages, user_id, anonymous_id } = body as {
    messages?: Array<{ role: string; content?: string; adaptive_card?: unknown }>;
    user_id?: string;
    anonymous_id?: string;
  };

  if (!messages?.length) {
    return NextResponse.json(
      { error: "messages array required" },
      { status: 400 }
    );
  }

  const { data: thread, error: threadError } = await supabase
    .from("chat_threads")
    .select("id, anonymous_id, user_id")
    .eq("id", id)
    .single();

  if (threadError || !thread) {
    return NextResponse.json({ error: "Thread not found" }, { status: 404 });
  }

  if (thread.user_id) {
    if (user_id !== thread.user_id) {
      return NextResponse.json(
        { error: "Thread access denied" },
        { status: 403 }
      );
    }
  } else if (thread.anonymous_id) {
    if (anonymous_id !== thread.anonymous_id) {
      return NextResponse.json(
        { error: "Thread access denied" },
        { status: 403 }
      );
    }
  } else {
    return NextResponse.json(
      { error: "Thread access denied" },
      { status: 403 }
    );
  }

  const rows = messages
    .filter((m) => m.role === "assistant" || m.role === "user")
    .map((m) => ({
      thread_id: id,
      role: m.role,
      content: m.content ?? null,
      adaptive_card: m.adaptive_card ?? null,
      channel: "web",
    }));

  if (rows.length === 0) {
    return NextResponse.json({ ok: true });
  }

  const { error } = await supabase.from("chat_messages").insert(rows);

  if (error) {
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }

  await supabase
    .from("chat_threads")
    .update({ updated_at: new Date().toISOString() })
    .eq("id", id);

  return NextResponse.json({ ok: true });
}
