import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json(
      { detail: "Partner account required. Your application may be pending approval." },
      { status: 403 }
    );
  }

  const supabase = createSupabaseServerClient();
  const { data: products } = await supabase
    .from("products")
    .select("id, name, is_available")
    .eq("partner_id", partnerId)
    .is("deleted_at", null);

  const productIds = (products ?? []).map((p) => p.id);
  if (productIds.length === 0) {
    return NextResponse.json({ inventory: [], products: products ?? [] });
  }

  const { data: inv } = await supabase
    .from("product_inventory")
    .select("*")
    .in("product_id", productIds);

  const invByProduct = new Map((inv ?? []).map((i) => [i.product_id, i]));

  const inventory = (products ?? []).map((p) => ({
    product_id: p.id,
    product_name: p.name,
    is_available: p.is_available,
    quantity: invByProduct.get(p.id)?.quantity ?? 0,
    low_stock_threshold: invByProduct.get(p.id)?.low_stock_threshold ?? 5,
    auto_unlist_when_zero: invByProduct.get(p.id)?.auto_unlist_when_zero ?? true,
  }));

  return NextResponse.json({ inventory });
}
