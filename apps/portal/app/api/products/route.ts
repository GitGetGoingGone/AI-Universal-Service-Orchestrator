import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const supabase = createSupabaseServerClient();
  const { data: products, error } = await supabase
    .from("products")
    .select("id, name, description, price, currency, product_type, unit, is_available, image_url, created_at, last_acp_push_at, last_acp_push_success")
    .eq("partner_id", partnerId)
    .is("deleted_at", null)
    .order("created_at", { ascending: false });

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  const list = products ?? [];
  const productIds = list.map((p) => p.id);
  let withInventory: typeof list = list;
  if (productIds.length > 0) {
    const { data: inv } = await supabase
      .from("product_inventory")
      .select("product_id, quantity, low_stock_threshold")
      .in("product_id", productIds);
    const invByProduct = new Map(
      (inv ?? []).map((i: { product_id: string; quantity?: number; low_stock_threshold?: number }) => [i.product_id, i])
    );
    withInventory = list.map((p) => {
      const row = invByProduct.get(p.id);
      return {
        ...p,
        quantity: row?.quantity ?? 0,
        low_stock_threshold: row?.low_stock_threshold ?? 5,
      };
    });
  }

  return NextResponse.json({ products: withInventory });
}

export async function POST(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const body = await request.json();
  const { name, description, price, product_type, unit } = body;

  if (!name || price == null) {
    return NextResponse.json(
      { detail: "name and price are required" },
      { status: 400 }
    );
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("products")
    .insert({
      partner_id: partnerId,
      name,
      description: description || null,
      price: Number(price),
      currency: "USD",
      product_type: product_type === "service" ? "service" : "product",
      unit: unit || "piece",
    })
    .select("id")
    .single();

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ id: data.id });
}
