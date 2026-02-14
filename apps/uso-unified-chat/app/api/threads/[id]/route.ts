import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { searchParams } = new URL(req.url);
  const anonymousId = searchParams.get("anonymous_id");

  const supabase = getSupabase();
  if (!supabase) {
    return NextResponse.json(
      { error: "Persistence not configured" },
      { status: 503 }
    );
  }

  const { data: thread, error: threadError } = await supabase
    .from("chat_threads")
    .select("id, anonymous_id, user_id, bundle_id, title, created_at")
    .eq("id", id)
    .single();

  if (threadError || !thread) {
    return NextResponse.json({ error: "Thread not found" }, { status: 404 });
  }

  if (thread.anonymous_id && anonymousId !== thread.anonymous_id) {
    return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
  }

  const { data: messages } = await supabase
    .from("chat_messages")
    .select("id, role, content, adaptive_card, created_at")
    .eq("thread_id", id)
    .order("created_at", { ascending: true });

  const { data: pendingApprovals } = await supabase
    .from("standing_intents")
    .select("id, intent_description, created_at")
    .eq("platform", "web")
    .eq("thread_id", id)
    .in("status", ["pending", "active"]);

  return NextResponse.json({
    thread: {
      id: thread.id,
      bundle_id: thread.bundle_id,
      title: thread.title,
      created_at: thread.created_at,
    },
    messages: (messages ?? []).map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      adaptiveCard: m.adaptive_card,
    })),
    pending_approvals: (pendingApprovals ?? []).map((a) => ({
      id: a.id,
      intent_description: a.intent_description,
      created_at: a.created_at,
    })),
  });
}

export async function PATCH(
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
  const { bundle_id, anonymous_id } = body as {
    bundle_id?: string;
    anonymous_id?: string;
  };

  const { data: thread } = await supabase
    .from("chat_threads")
    .select("anonymous_id")
    .eq("id", id)
    .single();

  if (!thread) {
    return NextResponse.json({ error: "Thread not found" }, { status: 404 });
  }
  if (thread.anonymous_id && anonymous_id !== thread.anonymous_id) {
    return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
  }

  const updates: Record<string, unknown> = {
    updated_at: new Date().toISOString(),
  };
  if (bundle_id !== undefined) updates.bundle_id = bundle_id;

  const { error } = await supabase
    .from("chat_threads")
    .update(updates)
    .eq("id", id);

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
  return NextResponse.json({ ok: true });
}
