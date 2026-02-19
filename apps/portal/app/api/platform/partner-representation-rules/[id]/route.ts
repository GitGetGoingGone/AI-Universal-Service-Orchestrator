import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase";
import { isPlatformAdmin } from "@/lib/auth";

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

    const updates: Record<string, unknown> = {
      updated_at: new Date().toISOString(),
    };
    if (body.admin_weight != null) {
      updates.admin_weight = Math.max(0, Math.min(10, Number(body.admin_weight)));
    }
    if (body.preferred_protocol != null) {
      const v = String(body.preferred_protocol).toUpperCase();
      if (["UCP", "MCP", "DB"].includes(v)) updates.preferred_protocol = v;
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("partner_representation_rules")
      .update(updates)
      .eq("id", id)
      .select()
      .single();

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json(data);
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
      .from("partner_representation_rules")
      .delete()
      .eq("id", id);

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
