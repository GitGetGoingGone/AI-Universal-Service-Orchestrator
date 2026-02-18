import { NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabase";

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { searchParams } = new URL(req.url);
  const anonymousId = searchParams.get("anonymous_id");
  const userId = searchParams.get("user_id");

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

  if (thread.user_id) {
    if (userId !== thread.user_id) {
      return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
    }
  } else if (thread.anonymous_id) {
    if (anonymousId !== thread.anonymous_id) {
      return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
    }
  } else {
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

  let latestOrder: {
    id: string;
    status: string;
    payment_status: string;
    total_amount: number;
    currency: string;
    created_at: string;
    items?: Array<{ item_name: string; quantity: number; total_price: number }>;
  } | null = null;

  if (thread.bundle_id) {
    const { data: orders } = await supabase
      .from("orders")
      .select("id, status, payment_status, total_amount, currency, created_at")
      .eq("bundle_id", thread.bundle_id)
      .eq("payment_status", "paid")
      .order("created_at", { ascending: false })
      .limit(1);

    if (orders?.[0]) {
      const o = orders[0];
      const { data: items } = await supabase
        .from("order_items")
        .select("item_name, quantity, total_price")
        .eq("order_id", o.id);
      latestOrder = {
        id: o.id,
        status: o.status ?? "unknown",
        payment_status: o.payment_status ?? "paid",
        total_amount: Number(o.total_amount ?? 0),
        currency: o.currency ?? "USD",
        created_at: o.created_at ?? "",
        items: (items ?? []).map((it) => ({
          item_name: it.item_name ?? "",
          quantity: it.quantity ?? 1,
          total_price: Number(it.total_price ?? 0),
        })),
      };
    }
  }

  return NextResponse.json({
    thread: {
      id: thread.id,
      bundle_id: thread.bundle_id,
      title: thread.title,
      created_at: thread.created_at,
      latest_order: latestOrder,
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
  const { bundle_id, anonymous_id, user_id } = body as {
    bundle_id?: string;
    anonymous_id?: string;
    user_id?: string;
  };

  const { data: thread } = await supabase
    .from("chat_threads")
    .select("anonymous_id, user_id")
    .eq("id", id)
    .single();

  if (!thread) {
    return NextResponse.json({ error: "Thread not found" }, { status: 404 });
  }
  if (thread.user_id) {
    if (user_id !== thread.user_id) {
      return NextResponse.json({ error: "Thread access denied" }, { status: 403 });
    }
  } else if (thread.anonymous_id && anonymous_id !== thread.anonymous_id) {
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
