import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";
import { encryptLlmKey, isEncryptionConfigured } from "@/lib/encrypt";

const API_TYPES = ["web_search", "weather", "events"] as const;

export async function GET() {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("external_api_providers")
      .select("id, name, api_type, base_url, extra_config, display_order, enabled, created_at, updated_at, api_key_encrypted")
      .order("display_order", { ascending: true })
      .order("api_type", { ascending: true });

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    const out = (data ?? []).map(({ api_key_encrypted: enc, ...r }) => ({
      ...r,
      has_key: !!enc,
    }));

    return NextResponse.json(out);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const body = await request.json();
    const { name, api_type, base_url, api_key } = body;

    if (!name || !api_type) {
      return NextResponse.json(
        { detail: "name and api_type are required" },
        { status: 400 }
      );
    }

    if (!API_TYPES.includes(api_type)) {
      return NextResponse.json(
        { detail: `api_type must be one of: ${API_TYPES.join(", ")}` },
        { status: 400 }
      );
    }

    let api_key_encrypted: string | null = null;
    if (api_key && typeof api_key === "string") {
      api_key_encrypted = isEncryptionConfigured()
        ? encryptLlmKey(api_key)
        : api_key;
    }

    const supabase = createSupabaseServerClient();
    const insertRow: Record<string, unknown> = {
      name: String(name),
      api_type,
      base_url: base_url ? String(base_url).trim() || null : null,
      api_key_encrypted,
      enabled: true,
      updated_at: new Date().toISOString(),
    };
    if (extra_config != null && typeof extra_config === "object" && !Array.isArray(extra_config)) {
      insertRow.extra_config = extra_config;
    }
    const { data, error } = await supabase
      .from("external_api_providers")
      .insert(insertRow)
      .select()
      .single();

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    const out = { ...data };
    delete (out as Record<string, unknown>).api_key_encrypted;
    (out as Record<string, unknown>).has_key = !!api_key_encrypted;

    return NextResponse.json(out);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
