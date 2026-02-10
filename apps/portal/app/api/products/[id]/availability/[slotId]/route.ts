import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

async function verifyProductAccess(productId: string, partnerId: string) {
  const supabase = createSupabaseServerClient();
  const { data } = await supabase
    .from("products")
    .select("id")
    .eq("id", productId)
    .eq("partner_id", partnerId)
    .is("deleted_at", null)
    .single();
  return !!data;
}

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string; slotId: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id: productId, slotId } = await params;
  const ok = await verifyProductAccess(productId, partnerId);
  if (!ok) return NextResponse.json({ detail: "Not found" }, { status: 404 });

  const body = await request.json();
  const supabase = createSupabaseServerClient();

  const { data: slot } = await supabase
    .from("product_availability")
    .select("id")
    .eq("id", slotId)
    .eq("product_id", productId)
    .single();

  if (!slot) return NextResponse.json({ detail: "Not found" }, { status: 404 });

  const updates: Record<string, unknown> = {};
  if (body.start_at != null) updates.start_at = body.start_at;
  if (body.end_at != null) updates.end_at = body.end_at;
  if (body.booking_mode != null) updates.booking_mode = body.booking_mode;

  const { error } = await supabase
    .from("product_availability")
    .update(updates)
    .eq("id", slotId);

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string; slotId: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id: productId, slotId } = await params;
  const ok = await verifyProductAccess(productId, partnerId);
  if (!ok) return NextResponse.json({ detail: "Not found" }, { status: 404 });

  const supabase = createSupabaseServerClient();
  const { error } = await supabase
    .from("product_availability")
    .delete()
    .eq("id", slotId)
    .eq("product_id", productId);

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}
