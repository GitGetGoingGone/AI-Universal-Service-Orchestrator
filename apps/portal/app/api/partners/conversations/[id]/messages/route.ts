import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

const HYBRID_RESPONSE_URL =
  process.env.HYBRID_RESPONSE_SERVICE_URL || "https://uso-hybrid-response.onrender.com";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id } = await params;
  const supabase = createSupabaseServerClient();

  const { data: conv } = await supabase
    .from("conversations")
    .select("id")
    .eq("id", id)
    .eq("partner_id", partnerId)
    .single();

  if (!conv) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  const { data: messages } = await supabase
    .from("messages")
    .select("id, content, sender_type, sender_name, sent_at, message_type")
    .eq("conversation_id", id)
    .order("sent_at", { ascending: true });

  return NextResponse.json({ messages: messages ?? [] });
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id } = await params;
  const body = await request.json();
  const content = body?.content as string;
  const senderType = (body?.sender_type as string) || "partner";

  if (!content || typeof content !== "string") {
    return NextResponse.json({ detail: "content required" }, { status: 400 });
  }

  const supabase = createSupabaseServerClient();

  const { data: conv } = await supabase
    .from("conversations")
    .select("id, order_id, bundle_id, partner_id")
    .eq("id", id)
    .eq("partner_id", partnerId)
    .single();

  if (!conv) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  const { data: partner } = await supabase
    .from("partners")
    .select("business_name, ai_auto_respond_enabled")
    .eq("id", partnerId)
    .single();

  const { data: msg, error } = await supabase
    .from("messages")
    .insert({
      conversation_id: id,
      sender_id: null,
      sender_type: senderType,
      sender_name: senderType === "partner" ? partner?.business_name ?? "Partner" : "Customer",
      content: content.trim(),
      message_type: "text",
      channel: "web",
      status: "sent",
    })
    .select()
    .single();

  if (error) return NextResponse.json({ detail: error.message }, { status: 500 });

  await supabase
    .from("conversations")
    .update({ updated_at: new Date().toISOString() })
    .eq("id", id);

  if (senderType === "customer" && partner?.ai_auto_respond_enabled) {
    const allowedOrderIds: string[] = [];
    if (conv.order_id) allowedOrderIds.push(conv.order_id);
    if (conv.bundle_id && allowedOrderIds.length === 0) {
      const { data: orders } = await supabase
        .from("orders")
        .select("id")
        .eq("bundle_id", conv.bundle_id);
      if (orders) allowedOrderIds.push(...orders.map((o: { id: string }) => o.id));
    }

    try {
      const res = await fetch(`${HYBRID_RESPONSE_URL}/api/v1/classify-and-respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          partner_id: partnerId,
          conversation_id: id,
          message_content: content.trim(),
          allowed_order_ids: allowedOrderIds.length > 0 ? allowedOrderIds : undefined,
        }),
      });
      if (res.ok) {
        const result = await res.json();
        if (result.ai_response) {
          const { data: aiMsg } = await supabase
            .from("messages")
            .insert({
              conversation_id: id,
              sender_id: null,
              sender_type: "ai",
              sender_name: "AI Assistant",
              content: result.ai_response,
              message_type: "text",
              channel: "web",
              status: "sent",
            })
            .select()
            .single();
          await supabase
            .from("conversations")
            .update({ updated_at: new Date().toISOString() })
            .eq("id", id);
          return NextResponse.json({ message: msg, ai_message: aiMsg });
        }
      }
    } catch {
      // AI flow failed; customer message already saved
    }
  }

  return NextResponse.json(msg);
}
