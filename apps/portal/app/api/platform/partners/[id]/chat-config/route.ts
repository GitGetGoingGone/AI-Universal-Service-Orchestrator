import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    if (!(await isPlatformAdmin())) {
      return NextResponse.json({ detail: "Platform admin access required" }, { status: 403 });
    }

    const { id } = await params;
    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("partner_chat_config")
      .select("*")
      .eq("partner_id", id)
      .single();

    if (error && error.code !== "PGRST116") {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json(data ?? { partner_id: id });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

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
    const { chat_widget_enabled, admin_e2e_enabled } = body;

    const updates: Record<string, unknown> = { updated_at: new Date().toISOString() };
    if (typeof chat_widget_enabled === "boolean") updates.chat_widget_enabled = chat_widget_enabled;
    if (typeof admin_e2e_enabled === "boolean") updates.admin_e2e_enabled = admin_e2e_enabled;

    if (Object.keys(updates).length <= 1) {
      return NextResponse.json(
        { detail: "Provide chat_widget_enabled and/or admin_e2e_enabled" },
        { status: 400 }
      );
    }

    const supabase = createSupabaseServerClient();
    const { data: existing } = await supabase
      .from("partner_chat_config")
      .select("id")
      .eq("partner_id", id)
      .single();

    if (existing) {
      const { data, error } = await supabase
        .from("partner_chat_config")
        .update(updates)
        .eq("partner_id", id)
        .select()
        .single();
      if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
      return NextResponse.json(data);
    }

    const { data, error } = await supabase
      .from("partner_chat_config")
      .insert({ partner_id: id, ...updates })
      .select()
      .single();
    if (error) return NextResponse.json({ detail: error.message }, { status: 500 });
    return NextResponse.json(data);
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
