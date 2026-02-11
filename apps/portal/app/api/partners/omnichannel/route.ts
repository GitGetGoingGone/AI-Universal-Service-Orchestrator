import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const supabase = createSupabaseServerClient();
  const { data } = await supabase
    .from("communication_preferences")
    .select("id, channel, channel_identifier, is_active")
    .eq("partner_id", partnerId);

  const whatsapp = (data ?? []).find((p) => p.channel === "whatsapp");
  const api = (data ?? []).find((p) => p.channel === "api");

  return NextResponse.json({
    whatsapp: whatsapp
      ? {
          id: whatsapp.id,
          phone: whatsapp.channel_identifier,
          isActive: whatsapp.is_active,
        }
      : null,
    api: api
      ? {
          id: api.id,
          webhookUrl: api.channel_identifier,
          isActive: api.is_active,
        }
      : null,
  });
}

export async function POST(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const body = await request.json();
  const channel = body?.channel as string;
  const phone = body?.phone as string | undefined;

  if (channel !== "whatsapp") {
    return NextResponse.json({ detail: "Only whatsapp channel supported" }, { status: 400 });
  }

  if (!phone || typeof phone !== "string") {
    return NextResponse.json({ detail: "phone is required for WhatsApp" }, { status: 400 });
  }

  const normalized = phone.replace(/\D/g, "");
  if (normalized.length < 10) {
    return NextResponse.json({ detail: "Invalid phone number" }, { status: 400 });
  }
  const formatted = normalized.startsWith("1") && normalized.length === 11 ? `+${normalized}` : `+1${normalized}`;

  const supabase = createSupabaseServerClient();
  const { data: existing } = await supabase
    .from("communication_preferences")
    .select("id")
    .eq("partner_id", partnerId)
    .eq("channel", "whatsapp")
    .single();

  if (existing) {
    const { data, error } = await supabase
      .from("communication_preferences")
      .update({
        channel_identifier: formatted,
        is_active: true,
        updated_at: new Date().toISOString(),
      })
      .eq("id", existing.id)
      .select()
      .single();
    if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
    return NextResponse.json(data);
  } else {
    const { data, error } = await supabase
      .from("communication_preferences")
      .insert({
        partner_id: partnerId,
        channel: "whatsapp",
        channel_identifier: formatted,
        is_active: true,
      })
      .select()
      .single();
    if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
    return NextResponse.json(data);
  }
}
