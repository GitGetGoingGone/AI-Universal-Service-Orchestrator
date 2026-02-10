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

    const { data, error } = await supabase
      .from("platform_config")
      .update(updates)
      .select()
      .limit(1)
      .single();

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
