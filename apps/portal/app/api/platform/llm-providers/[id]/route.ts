import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";
import { encryptLlmKey, isEncryptionConfigured } from "@/lib/encrypt";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { id } = await params;
    const body = await request.json();
    const { name, provider_type, endpoint, api_key, model } = body;

    const updates: Record<string, unknown> = {
      updated_at: new Date().toISOString(),
    };

    if (name != null) updates.name = String(name);
    if (provider_type != null) {
      const valid = ["azure", "gemini", "openrouter", "custom"];
      if (!valid.includes(provider_type)) {
        return NextResponse.json({ detail: "Invalid provider_type" }, { status: 400 });
      }
      updates.provider_type = provider_type;
    }
    if (endpoint !== undefined) updates.endpoint = endpoint ? String(endpoint) : null;
    if (model != null) updates.model = String(model);

    if (api_key !== undefined && api_key !== null && api_key !== "") {
      updates.api_key_encrypted = isEncryptionConfigured()
        ? encryptLlmKey(String(api_key))
        : String(api_key);
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("llm_providers")
      .update(updates)
      .eq("id", id)
      .select()
      .single();

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    const out = { ...data };
    delete (out as Record<string, unknown>).api_key_encrypted;
    (out as Record<string, unknown>).has_key = !!data?.api_key_encrypted;

    return NextResponse.json(out);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { id } = await params;

    const supabase = createSupabaseServerClient();

    const { data: cfg } = await supabase
      .from("platform_config")
      .select("active_llm_provider_id")
      .limit(1)
      .single();

    if (cfg?.active_llm_provider_id === id) {
      return NextResponse.json(
        { detail: "Cannot delete the active LLM provider. Set another as active first." },
        { status: 400 }
      );
    }

    const { error } = await supabase.from("llm_providers").delete().eq("id", id);

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json({ deleted: true });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
