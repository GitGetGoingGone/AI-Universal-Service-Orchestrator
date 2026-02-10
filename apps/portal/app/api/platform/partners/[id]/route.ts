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
    const { verification_status, is_active } = body;

    const supabase = createSupabaseServerClient();
    const updates: Record<string, unknown> = { updated_at: new Date().toISOString() };

    if (verification_status && ["approved", "rejected"].includes(verification_status)) {
      updates.verification_status = verification_status;
      updates.verified_at = verification_status === "approved" ? new Date().toISOString() : null;
    }
    if (typeof is_active === "boolean") {
      updates.is_active = is_active;
    }

    const hasUpdate = (verification_status && ["approved", "rejected"].includes(verification_status)) || typeof is_active === "boolean";
    if (!hasUpdate) {
      return NextResponse.json(
        { detail: "Provide verification_status and/or is_active" },
        { status: 400 }
      );
    }

    const { data, error } = await supabase
      .from("partners")
      .update(updates)
      .eq("id", id)
      .select("id")
      .single();

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json({ id: data.id, ...updates });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}

/** Soft-delete: set is_active = false so partner can be removed for testing. */
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
      .from("partners")
      .update({ is_active: false, updated_at: new Date().toISOString() })
      .eq("id", id);

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json({ removed: true });
  } catch (err) {
    return NextResponse.json({ detail: "Internal server error" }, { status: 500 });
  }
}
