import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";
import crypto from "crypto";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const supabase = createSupabaseServerClient();

  const { data: prefs } = await supabase
    .from("communication_preferences")
    .select("id, channel, channel_identifier, is_active")
    .eq("partner_id", partnerId);

  const { data: keys } = await supabase
    .from("partner_api_keys")
    .select("id, key_prefix, name, last_used_at, expires_at, is_active, created_at")
    .eq("partner_id", partnerId)
    .order("created_at", { ascending: false });

  const { data: availInt } = await supabase
    .from("availability_integrations")
    .select("id, integration_type, provider, is_active, last_sync_at, last_sync_status")
    .eq("partner_id", partnerId);

  const apiPref = (prefs ?? []).find((p) => p.channel === "api");
  const webhookUrl = apiPref?.channel_identifier ?? "";

  return NextResponse.json({
    webhookUrl,
    apiKeys: keys ?? [],
    availabilityIntegrations: availInt ?? [],
  });
}

export async function POST(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const body = await request.json();
  const type = body?.type as string;

  if (type === "webhook") {
    const url = body?.url as string | undefined;
    if (!url || typeof url !== "string") {
      return NextResponse.json({ detail: "url is required" }, { status: 400 });
    }
    const supabase = createSupabaseServerClient();
    const { data: existing } = await supabase
      .from("communication_preferences")
      .select("id")
      .eq("partner_id", partnerId)
      .eq("channel", "api")
      .single();

    if (existing) {
      const { data, error } = await supabase
        .from("communication_preferences")
        .update({ channel_identifier: url.trim(), is_active: true, updated_at: new Date().toISOString() })
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
          channel: "api",
          channel_identifier: url.trim(),
          is_active: true,
        })
        .select()
        .single();
      if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
      return NextResponse.json(data);
    }
  }

  if (type === "api_key") {
    const name = (body?.name as string) || "API Key";
    const rawKey = `uso_${crypto.randomBytes(32).toString("hex")}`;
    const secret = process.env.API_KEY_SECRET || process.env.SUPABASE_SECRET_KEY || "fallback-api-key-secret";
    const keyHash = crypto.createHmac("sha256", secret).update(rawKey).digest("hex");
    const keyPrefix = rawKey.slice(0, 12);

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("partner_api_keys")
      .insert({
        partner_id: partnerId,
        key_hash: keyHash,
        key_prefix: keyPrefix,
        name: name.trim(),
        is_active: true,
      })
      .select()
      .single();

    if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
    return NextResponse.json({ ...data, rawKey });
  }

  return NextResponse.json({ detail: "Unknown type" }, { status: 400 });
}
