import { NextResponse } from "next/server";
import { getPartnerIdFromApiKey } from "@/lib/api-key-auth";
import { createSupabaseServerClient } from "@/lib/supabase";

const HYBRID_RESPONSE_URL =
  process.env.HYBRID_RESPONSE_SERVICE_URL || "https://uso-hybrid-response.onrender.com";

/**
 * POST /api/webhooks/conversations/customer-message
 * Incoming customer message from external sources (WhatsApp, etc.).
 * Auth: Bearer <partner_api_key> or X-API-Key: <partner_api_key>
 * Body: { conversation_id: string, content: string }
 */
export async function POST(request: Request) {
  const partnerId = await getPartnerIdFromApiKey(request);
  if (!partnerId) {
    return NextResponse.json({ detail: "Invalid or missing API key" }, { status: 401 });
  }

  let body: { conversation_id?: string; content?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON" }, { status: 400 });
  }

  const conversationId = body?.conversation_id;
  const content = body?.content;

  if (!conversationId || typeof conversationId !== "string") {
    return NextResponse.json({ detail: "conversation_id required" }, { status: 400 });
  }
  if (!content || typeof content !== "string") {
    return NextResponse.json({ detail: "content required" }, { status: 400 });
  }

  const supabase = createSupabaseServerClient();
  const { data: conv } = await supabase
    .from("conversations")
    .select("id, order_id, bundle_id, partner_id")
    .eq("id", conversationId)
    .eq("partner_id", partnerId)
    .single();

  if (!conv) {
    return NextResponse.json({ detail: "Conversation not found" }, { status: 404 });
  }

  const { data: partner } = await supabase
    .from("partners")
    .select("business_name, ai_auto_respond_enabled")
    .eq("id", partnerId)
    .single();

  const { data: msg, error } = await supabase
    .from("messages")
    .insert({
      conversation_id: conversationId,
      sender_id: null,
      sender_type: "customer",
      sender_name: "Customer",
      content: content.trim(),
      message_type: "text",
      channel: "webhook",
      status: "sent",
    })
    .select()
    .single();

  if (error) return NextResponse.json({ detail: error.message }, { status: 500 });

  await supabase
    .from("conversations")
    .update({ updated_at: new Date().toISOString() })
    .eq("id", conversationId);

  if (partner?.ai_auto_respond_enabled) {
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
          conversation_id: conversationId,
          message_content: content.trim(),
          allowed_order_ids: allowedOrderIds.length > 0 ? allowedOrderIds : undefined,
        }),
      });
      if (res.ok) {
        const result = await res.json();
        if (result.ai_response) {
          await supabase.from("messages").insert({
            conversation_id: conversationId,
            sender_id: null,
            sender_type: "ai",
            sender_name: "AI Assistant",
            content: result.ai_response,
            message_type: "text",
            channel: "webhook",
            status: "sent",
          });
          await supabase
            .from("conversations")
            .update({ updated_at: new Date().toISOString() })
            .eq("id", conversationId);
        }
      }
    } catch {
      // AI flow failed; customer message already saved
    }
  }

  return NextResponse.json({ message: msg, received: true });
}
