import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id } = await params;
  const body = await request.json();
  const role = body?.role as string | undefined;
  const isActive = body?.is_active as boolean | undefined;

  const updates: Record<string, unknown> = {};
  if (role !== undefined) {
    const validRoles = ["owner", "admin", "member"];
    if (!validRoles.includes(role)) {
      return NextResponse.json({ detail: "Invalid role" }, { status: 400 });
    }
    updates.role = role;
  }
  if (isActive !== undefined) updates.is_active = isActive;

  if (Object.keys(updates).length === 0) {
    return NextResponse.json({ detail: "No updates" }, { status: 400 });
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("partner_members")
    .update(updates)
    .eq("id", id)
    .eq("partner_id", partnerId)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: error.code === "PGRST116" ? 404 : 500 });
  }
  return NextResponse.json(data);
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id } = await params;
  const supabase = createSupabaseServerClient();
  const { error } = await supabase
    .from("partner_members")
    .delete()
    .eq("id", id)
    .eq("partner_id", partnerId);

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: error.code === "PGRST116" ? 404 : 500 });
  }
  return new NextResponse(null, { status: 204 });
}
