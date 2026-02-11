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

  const { id } = await params;
  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("products")
    .select("*")
    .eq("id", id)
    .eq("partner_id", partnerId)
    .is("deleted_at", null)
    .single();

  if (error || !data) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  return NextResponse.json(data);
}

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

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("products")
    .update({
      ...(body.name != null && { name: body.name }),
      ...(body.description != null && { description: body.description }),
      ...(body.price != null && { price: Number(body.price) }),
      ...(body.product_type != null && { product_type: body.product_type === "service" ? "service" : "product" }),
      ...(body.unit != null && { unit: body.unit }),
      ...(body.is_available != null && { is_available: body.is_available }),
      ...(body.url !== undefined && { url: body.url ?? null }),
      ...(body.brand !== undefined && { brand: body.brand ?? null }),
      ...(body.image_url !== undefined && { image_url: body.image_url ?? null }),
      ...(body.is_eligible_search !== undefined && { is_eligible_search: !!body.is_eligible_search }),
      ...(body.is_eligible_checkout !== undefined && { is_eligible_checkout: !!body.is_eligible_checkout }),
      ...(body.availability !== undefined && { availability: body.availability ?? "in_stock" }),
      ...(body.target_countries !== undefined && {
        target_countries: Array.isArray(body.target_countries)
          ? body.target_countries
          : body.target_countries == null || body.target_countries === ""
            ? null
            : typeof body.target_countries === "string"
              ? body.target_countries.split(",").map((s: string) => s.trim()).filter(Boolean)
              : null,
      }),
      updated_at: new Date().toISOString(),
    })
    .eq("id", id)
    .eq("partner_id", partnerId)
    .select("id")
    .single();

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ id: data.id });
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
    .from("products")
    .update({ deleted_at: new Date().toISOString() })
    .eq("id", id)
    .eq("partner_id", partnerId);

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ success: true });
}
