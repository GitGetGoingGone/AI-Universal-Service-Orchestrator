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
  const { data: product } = await supabase
    .from("products")
    .select("id")
    .eq("id", id)
    .eq("partner_id", partnerId)
    .is("deleted_at", null)
    .single();

  if (!product) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  const { data, error } = await supabase
    .from("product_availability")
    .select("*")
    .eq("product_id", id)
    .order("start_at");

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ availability: data ?? [] });
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const { id } = await params;
  const body = await request.json();
  const { start_at, end_at, booking_mode = "auto_book", capacity = 1 } = body;

  if (!start_at || !end_at) {
    return NextResponse.json(
      { detail: "start_at and end_at required" },
      { status: 400 }
    );
  }

  const supabase = createSupabaseServerClient();
  const { data: product } = await supabase
    .from("products")
    .select("id")
    .eq("id", id)
    .eq("partner_id", partnerId)
    .is("deleted_at", null)
    .single();

  if (!product) {
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  }

  const { data, error } = await supabase
    .from("product_availability")
    .insert({
      product_id: id,
      slot_type: "manual",
      start_at,
      end_at,
      booking_mode: booking_mode || "auto_book",
      capacity: Math.max(1, Number(capacity) || 1),
    })
    .select("id")
    .single();

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ id: data.id });
}
