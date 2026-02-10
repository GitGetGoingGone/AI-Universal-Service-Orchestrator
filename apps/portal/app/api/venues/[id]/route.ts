import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "Partner account required." }, { status: 403 });
  }

  const { id } = await params;
  const body = await request.json();

  const supabase = createSupabaseServerClient();
  const updates: Record<string, unknown> = {};
  if (body.name != null) updates.name = body.name;
  if (body.address != null) updates.address = body.address;
  if (body.timezone != null) updates.timezone = body.timezone;
  if (body.is_active != null) updates.is_active = Boolean(body.is_active);

  const { data, error } = await supabase
    .from("partner_venues")
    .update(updates)
    .eq("id", id)
    .eq("partner_id", partnerId)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json(data);
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "Partner account required." }, { status: 403 });
  }

  const { id } = await params;
  const supabase = createSupabaseServerClient();

  const { error } = await supabase
    .from("partner_venues")
    .delete()
    .eq("id", id)
    .eq("partner_id", partnerId);

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}
