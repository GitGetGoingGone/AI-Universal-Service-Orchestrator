import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("partner_chat_config")
    .select("*")
    .eq("partner_id", partnerId)
    .single();

  if (error && error.code !== "PGRST116") {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  if (!data) {
    return NextResponse.json({
      partner_id: partnerId,
      primary_color: "#1976d2",
      secondary_color: "#424242",
      font_family: "Inter, sans-serif",
      font_size_px: 14,
      logo_url: null,
      welcome_message: "How can I help you today?",
      embed_enabled: false,
      embed_domains: [],
      e2e_add_to_bundle: true,
      e2e_checkout: true,
      e2e_payment: true,
      chat_widget_enabled: true,
      admin_e2e_enabled: true,
      chat_typing_enabled: true,
      chat_typing_speed_ms: 30,
    });
  }

  return NextResponse.json(data);
}

export async function PATCH(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const body = await request.json();
  const updates: Record<string, unknown> = {};
  const allowed = [
    "primary_color",
    "secondary_color",
    "font_family",
    "font_size_px",
    "logo_url",
    "welcome_message",
    "embed_enabled",
    "embed_domains",
    "e2e_add_to_bundle",
    "e2e_checkout",
    "e2e_payment",
    "chat_typing_enabled",
    "chat_typing_speed_ms",
  ];
  for (const key of allowed) {
    if (body[key] !== undefined) updates[key] = body[key];
  }
  updates.updated_at = new Date().toISOString();

  if (Object.keys(updates).length <= 1) {
    return NextResponse.json({ detail: "No updates" }, { status: 400 });
  }

  const supabase = createSupabaseServerClient();
  const { data: existing } = await supabase
    .from("partner_chat_config")
    .select("id")
    .eq("partner_id", partnerId)
    .single();

  if (existing) {
    const { data, error } = await supabase
      .from("partner_chat_config")
      .update(updates)
      .eq("partner_id", partnerId)
      .select()
      .single();
    if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
    return NextResponse.json(data);
  }

  const { data, error } = await supabase
    .from("partner_chat_config")
    .insert({ partner_id: partnerId, ...updates })
    .select()
    .single();
  if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
  return NextResponse.json(data);
}
