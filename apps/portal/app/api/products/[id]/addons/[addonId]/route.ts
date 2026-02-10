import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string; addonId: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id: productId, addonId } = await params;
  const body = await request.json();
  const { name, price_delta, is_required } = body;

  const supabase = createSupabaseServerClient();
  const { data: product } = await supabase
    .from("products")
    .select("id")
    .eq("id", productId)
    .eq("partner_id", partnerId)
    .is("deleted_at", null)
    .single();

  if (!product) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  const updates: Record<string, unknown> = {};
  if (name != null) updates.name = String(name).trim();
  if (price_delta != null) updates.price_delta = Number(price_delta);
  if (is_required != null) updates.is_required = Boolean(is_required);

  if (Object.keys(updates).length === 0) {
    return NextResponse.json({ detail: "No updates provided" }, { status: 400 });
  }

  const { data, error } = await supabase
    .from("product_modifiers")
    .update(updates)
    .eq("id", addonId)
    .eq("product_id", productId)
    .select("id, name, price_delta, is_required")
    .single();

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json(data);
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string; addonId: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id: productId, addonId } = await params;
  const supabase = createSupabaseServerClient();

  const { data: product } = await supabase
    .from("products")
    .select("id")
    .eq("id", productId)
    .eq("partner_id", partnerId)
    .is("deleted_at", null)
    .single();

  if (!product) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  const { error } = await supabase
    .from("product_modifiers")
    .delete()
    .eq("id", addonId)
    .eq("product_id", productId);

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ deleted: true });
}
