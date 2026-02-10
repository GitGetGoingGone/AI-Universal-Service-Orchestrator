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
  if (body.promo_type != null) updates.promo_type = body.promo_type;
  if (body.value != null) updates.value = Number(body.value);
  if (body.start_at != null) updates.start_at = body.start_at;
  if (body.end_at != null) updates.end_at = body.end_at;
  if (body.is_active != null) updates.is_active = Boolean(body.is_active);

  const { data, error } = await supabase
    .from("partner_promotions")
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
    .from("partner_promotions")
    .delete()
    .eq("id", id)
    .eq("partner_id", partnerId);

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}
