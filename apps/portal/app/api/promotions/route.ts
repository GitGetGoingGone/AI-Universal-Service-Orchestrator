import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "Partner account required." }, { status: 403 });
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("partner_promotions")
    .select("*")
    .eq("partner_id", partnerId)
    .order("start_at", { ascending: false });

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ promotions: data ?? [] });
}

export async function POST(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "Partner account required." }, { status: 403 });
  }

  const body = await request.json();
  const { name, promo_type, value, start_at, end_at } = body;

  if (!name || !promo_type || !start_at || !end_at) {
    return NextResponse.json(
      { detail: "name, promo_type, start_at, end_at required" },
      { status: 400 }
    );
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("partner_promotions")
    .insert({
      partner_id: partnerId,
      name,
      promo_type,
      value: value != null ? Number(value) : null,
      start_at,
      end_at,
      is_active: true,
    })
    .select("id")
    .single();

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ id: data.id });
}
