import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";
import { encryptLlmKey, isEncryptionConfigured } from "@/lib/encrypt";

const API_TYPES = ["web_search", "weather", "events"] as const;

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

    const patch: Record<string, unknown> = { updated_at: new Date().toISOString() };
    if (body.name !== undefined) patch.name = String(body.name);
    if (body.api_type !== undefined) {
      if (!API_TYPES.includes(body.api_type)) {
        return NextResponse.json(
          { detail: `api_type must be one of: ${API_TYPES.join(", ")}` },
          { status: 400 }
        );
      }
      patch.api_type = body.api_type;
    }
    if (body.base_url !== undefined) patch.base_url = body.base_url ? String(body.base_url).trim() : null;
    if (body.enabled !== undefined) patch.enabled = Boolean(body.enabled);
    if (body.api_key !== undefined && body.api_key !== "") {
      patch.api_key_encrypted = isEncryptionConfigured()
        ? encryptLlmKey(String(body.api_key))
        : body.api_key;
    }
    if (body.extra_config !== undefined) {
      patch.extra_config =
        body.extra_config != null && typeof body.extra_config === "object" && !Array.isArray(body.extra_config)
          ? body.extra_config
          : {};
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("external_api_providers")
      .update(patch)
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
    const { error } = await supabase
      .from("external_api_providers")
      .delete()
      .eq("id", id);

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json({ deleted: true });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
