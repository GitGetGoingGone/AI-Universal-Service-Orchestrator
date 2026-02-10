import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id: productId } = await params;
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

  const { data, error } = await supabase
    .from("product_modifiers")
    .select("id, name, price_delta, is_required")
    .eq("product_id", productId)
    .order("created_at");

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ addons: data ?? [] });
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id: productId } = await params;
  const body = await request.json();
  const { name, price_delta, is_required } = body;

  if (!name || typeof name !== "string" || name.trim() === "") {
    return NextResponse.json({ detail: "name is required" }, { status: 400 });
  }

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

  const { data, error } = await supabase
    .from("product_modifiers")
    .insert({
      product_id: productId,
      name: name.trim(),
      price_delta: Number(price_delta) || 0,
      is_required: Boolean(is_required),
    })
    .select("id, name, price_delta, is_required")
    .single();

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json(data);
}
