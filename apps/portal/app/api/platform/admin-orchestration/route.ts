import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET() {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("admin_orchestration_settings")
      .select("id, global_tone, model_temperature, autonomy_level, discovery_timeout_ms, ucp_prioritized")
      .limit(1)
      .single();

    if (error && error.code !== "PGRST116") {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json(
      data ?? {
        global_tone: "warm, elegant, memorable",
        model_temperature: 0.7,
        autonomy_level: "balanced",
        discovery_timeout_ms: 5000,
        ucp_prioritized: false,
      }
    );
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

export async function PATCH(request: Request) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const body = await request.json();
    const supabase = createSupabaseServerClient();

    const updates: Record<string, unknown> = {
      updated_at: new Date().toISOString(),
    };
    if (body.global_tone != null) updates.global_tone = String(body.global_tone).trim();
    if (body.model_temperature != null) {
      const t = Number(body.model_temperature);
      updates.model_temperature = Math.max(0, Math.min(2, t));
    }
    if (body.autonomy_level != null) {
      const v = String(body.autonomy_level);
      if (["conservative", "balanced", "aggressive"].includes(v)) {
        updates.autonomy_level = v;
      }
    }
    if (body.discovery_timeout_ms != null) {
      const t = Number(body.discovery_timeout_ms);
      updates.discovery_timeout_ms = Math.max(500, Math.min(60000, t));
    }
    if (body.ucp_prioritized != null) updates.ucp_prioritized = Boolean(body.ucp_prioritized);

    const { data: existing } = await supabase
      .from("admin_orchestration_settings")
      .select("id")
      .limit(1)
      .single();

    let result: { data: unknown; error: { message: string } | null };
    if (existing?.id) {
      result = await supabase
        .from("admin_orchestration_settings")
        .update(updates)
        .eq("id", existing.id)
        .select()
        .single();
    } else {
      result = await supabase
        .from("admin_orchestration_settings")
        .insert(updates)
        .select()
        .single();
    }

    if (result.error) {
      return NextResponse.json({ detail: result.error.message }, { status: 500 });
    }

    return NextResponse.json(result.data);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
