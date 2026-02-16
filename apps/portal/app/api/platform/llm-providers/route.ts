import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";
import { encryptLlmKey, isEncryptionConfigured } from "@/lib/encrypt";

export async function GET() {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("llm_providers")
      .select("id, name, provider_type, endpoint, model, display_order, created_at, updated_at, api_key_encrypted")
      .order("display_order", { ascending: true })
      .order("created_at", { ascending: true });

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
    const { name, provider_type, endpoint, api_key, model } = body;

    if (!name || !provider_type || !model) {
      return NextResponse.json(
        { detail: "name, provider_type, and model are required" },
        { status: 400 }
      );
    }

    const validTypes = ["azure", "gemini", "openrouter", "custom", "openai"];
    if (!validTypes.includes(provider_type)) {
      return NextResponse.json(
        { detail: "provider_type must be azure, gemini, openrouter, custom, or openai" },
        { status: 400 }
      );
    }

    if ((provider_type === "azure" || provider_type === "custom") && !endpoint) {
      return NextResponse.json(
        { detail: "endpoint is required for azure and custom providers" },
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
    const { data, error } = await supabase
      .from("llm_providers")
      .insert({
        name: String(name),
        provider_type,
        endpoint: endpoint ? String(endpoint) : null,
        api_key_encrypted,
        model: String(model),
        updated_at: new Date().toISOString(),
      })
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
