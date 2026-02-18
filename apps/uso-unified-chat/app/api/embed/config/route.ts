import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_SECRET_KEY;

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const partnerId = searchParams.get("partner_id");
  if (!partnerId) {
    return NextResponse.json({ error: "partner_id required" }, { status: 400 });
  }

  if (!supabaseUrl || !supabaseServiceKey) {
    return NextResponse.json(
      { error: "Embed config not configured", disabled: true },
      { status: 503 }
    );
  }

  const supabase = createClient(supabaseUrl, supabaseServiceKey);
  const [partnerResult, platformResult] = await Promise.all([
    supabase.from("partner_chat_config").select("*").eq("partner_id", partnerId).single(),
    supabase.from("platform_config").select("thinking_ui, thinking_messages").limit(1).single(),
  ]);

  const { data, error } = partnerResult;
  if (error && error.code !== "PGRST116") {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  type PlatformThinking = { thinking_ui?: { font_size_px?: number; color?: string; animation_type?: string; animation_speed_ms?: number }; thinking_messages?: Record<string, string> };
  const platformData = platformResult.data as PlatformThinking | null;
  const thinkingUi = platformData?.thinking_ui ?? {
    font_size_px: 14,
    color: "#94a3b8",
    animation_type: "dots",
    animation_speed_ms: 1000,
  };
  const thinkingMessages = platformData?.thinking_messages ?? {};

  const config = data ?? {
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
  };

  const chatEnabled = config.chat_widget_enabled !== false;
  const e2eEnabled = config.admin_e2e_enabled !== false;

  if (!chatEnabled) {
    return NextResponse.json({
      disabled: true,
      message: "Chat unavailable",
    });
  }

  // Domain allowlist: optional parent_origin from embed iframe query param
  const parentOrigin = searchParams.get("parent_origin");
  const embedDomains = Array.isArray(config.embed_domains)
    ? config.embed_domains
    : [];
  if (
    config.embed_enabled === true &&
    embedDomains.length > 0 &&
    parentOrigin
  ) {
    const allowed = embedDomains.some(
      (d: string) =>
        parentOrigin === d ||
        parentOrigin.endsWith("." + d) ||
        d === "*"
    );
    if (!allowed) {
      return NextResponse.json({
        disabled: true,
        message: "Embed not allowed for this domain",
      });
    }
  }

  return NextResponse.json({
    partner_id: partnerId,
    primary_color: config.primary_color ?? "#1976d2",
    secondary_color: config.secondary_color ?? "#424242",
    font_family: config.font_family ?? "Inter, sans-serif",
    font_size_px: config.font_size_px ?? 14,
    logo_url: config.logo_url ?? null,
    welcome_message: config.welcome_message ?? "How can I help you today?",
    e2e_add_to_bundle: e2eEnabled && (config.e2e_add_to_bundle !== false),
    e2e_checkout: e2eEnabled && (config.e2e_checkout !== false),
    e2e_payment: e2eEnabled && (config.e2e_payment !== false),
    chat_typing_enabled: config.chat_typing_enabled !== false,
    chat_typing_speed_ms: Math.max(10, Math.min(200, config.chat_typing_speed_ms ?? 30)),
    thinking_ui: thinkingUi,
    thinking_messages: thinkingMessages,
  });
}
