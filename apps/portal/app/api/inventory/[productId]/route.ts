import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ productId: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "Partner account required." }, { status: 403 });
  }

  const { productId } = await params;

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

  const { data: inv } = await supabase
    .from("product_inventory")
    .select("*")
    .eq("product_id", productId)
    .single();

  return NextResponse.json(
    inv ?? {
      product_id: productId,
      quantity: 0,
      low_stock_threshold: 5,
      auto_unlist_when_zero: true,
    }
  );
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ productId: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "Partner account required." }, { status: 403 });
  }

  const { productId } = await params;
  const body = await request.json();

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

  const { quantity, low_stock_threshold, auto_unlist_when_zero } = body;

  const { data: existing } = await supabase
    .from("product_inventory")
    .select("id")
    .eq("product_id", productId)
    .single();

  if (existing) {
    const newQuantity = quantity != null ? Number(quantity) : undefined;
    const { data, error } = await supabase
      .from("product_inventory")
      .update({
        quantity: newQuantity,
        low_stock_threshold: low_stock_threshold != null ? Number(low_stock_threshold) : undefined,
        auto_unlist_when_zero: auto_unlist_when_zero != null ? Boolean(auto_unlist_when_zero) : undefined,
        updated_at: new Date().toISOString(),
      })
      .eq("product_id", productId)
      .select()
      .single();

    if (error) return NextResponse.json({ detail: error.message }, { status: 500 });

    // Auto-unlist when quantity is 0 and flag is set
    const inv = data;
    const doUnlist = (inv.quantity === 0 && (inv.auto_unlist_when_zero ?? true)) || (newQuantity === 0 && (auto_unlist_when_zero ?? true));
    if (doUnlist) {
      await supabase.from("products").update({ is_available: false }).eq("id", productId);
    }

    return NextResponse.json(data);
  } else {
    const { data, error } = await supabase
      .from("product_inventory")
      .insert({
        product_id: productId,
        quantity: quantity ?? 0,
        low_stock_threshold: low_stock_threshold ?? 5,
        auto_unlist_when_zero: auto_unlist_when_zero ?? true,
      })
      .select()
      .single();

    if (error) return NextResponse.json({ detail: error.message }, { status: 500 });

    // Auto-unlist when quantity is 0 and flag is set
    const qty = data?.quantity ?? quantity ?? 0;
    const doUnlist = qty === 0 && (data?.auto_unlist_when_zero ?? auto_unlist_when_zero ?? true);
    if (doUnlist) {
      await supabase.from("products").update({ is_available: false }).eq("id", productId);
    }

    return NextResponse.json(data);
  }
}
