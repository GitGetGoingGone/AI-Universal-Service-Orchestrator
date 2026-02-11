import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { searchParams } = new URL(request.url);
  const filter = searchParams.get("filter") || "all";
  const myMemberId = searchParams.get("my_member_id") || "";

  const supabase = createSupabaseServerClient();
  let q = supabase
    .from("conversations")
    .select("id, title, status, order_id, bundle_id, assigned_to_member_id, partner_id, created_at, updated_at")
    .eq("partner_id", partnerId)
    .order("updated_at", { ascending: false });

  if (filter === "unassigned") {
    q = q.is("assigned_to_member_id", null);
  } else if (filter === "mine" && myMemberId) {
    q = q.eq("assigned_to_member_id", myMemberId);
  }

  const { data: conversations } = await q;

  const convIds = (conversations ?? []).map((c) => c.id);
  if (convIds.length === 0) {
    return NextResponse.json({ conversations: [], lastMessages: {} });
  }

  const { data: lastMessages } = await supabase
    .from("messages")
    .select("conversation_id, content, sent_at")
    .in("conversation_id", convIds)
    .order("sent_at", { ascending: false });

  const byConv = (lastMessages ?? []).reduce(
    (acc, m) => {
      const cid = m.conversation_id as string;
      if (!acc[cid]) acc[cid] = m;
      return acc;
    },
    {} as Record<string, { content: string; sent_at: string }>
  );

  return NextResponse.json({
    conversations: conversations ?? [],
    lastMessages: byConv,
  });
}

export async function POST(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const body = await request.json();
  const title = (body?.title as string) || "New conversation";
  const orderId = body?.order_id as string | undefined;
  const bundleId = body?.bundle_id as string | undefined;

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("conversations")
    .insert({
      partner_id: partnerId,
      title,
      order_id: orderId || null,
      bundle_id: bundleId || null,
      status: "active",
    })
    .select()
    .single();

  if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
  return NextResponse.json(data);
}
