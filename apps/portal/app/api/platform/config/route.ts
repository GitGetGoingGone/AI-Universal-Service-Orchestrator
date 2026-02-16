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
      .from("platform_config")
      .select("*")
      .limit(1)
      .single();

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json(data ?? {});
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
    if (body.commission_rate_pct != null)
      updates.commission_rate_pct = Number(body.commission_rate_pct);
    if (body.discovery_relevance_threshold != null)
      updates.discovery_relevance_threshold = Number(body.discovery_relevance_threshold);
    if (body.enable_self_registration != null)
      updates.enable_self_registration = Boolean(body.enable_self_registration);
    if (body.enable_chatgpt != null)
      updates.enable_chatgpt = Boolean(body.enable_chatgpt);
    if (body.feature_flags != null)
      updates.feature_flags = body.feature_flags;
    if (body.llm_provider != null)
      updates.llm_provider = String(body.llm_provider);
    if (body.llm_model != null)
      updates.llm_model = String(body.llm_model);
    if (body.llm_temperature != null) {
      const t = Number(body.llm_temperature);
      updates.llm_temperature = Math.max(0, Math.min(1, t));
    }
    if (body.active_llm_provider_id !== undefined)
      updates.active_llm_provider_id = body.active_llm_provider_id ? String(body.active_llm_provider_id) : null;
    if (body.ranking_enabled != null)
      updates.ranking_enabled = Boolean(body.ranking_enabled);
    if (body.ranking_policy != null)
      updates.ranking_policy = body.ranking_policy;
    if (body.ranking_edge_cases != null)
      updates.ranking_edge_cases = body.ranking_edge_cases;
    if (body.sponsorship_pricing != null)
      updates.sponsorship_pricing = body.sponsorship_pricing;

    const { data: existing } = await supabase
      .from("platform_config")
      .select("id")
      .limit(1)
      .single();

    let data: unknown;
    let error: { message: string } | null = null;

    if (existing?.id) {
      const result = await supabase
        .from("platform_config")
        .update(updates)
        .eq("id", existing.id)
        .select()
        .single();
      data = result.data;
      error = result.error;
    } else {
      const result = await supabase
        .from("platform_config")
        .insert(updates)
        .select()
        .single();
      data = result.data;
      error = result.error;
    }

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
