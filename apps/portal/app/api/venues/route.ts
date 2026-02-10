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
    .from("partner_venues")
    .select("*")
    .eq("partner_id", partnerId)
    .order("name");

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ venues: data ?? [] });
}

export async function POST(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "Partner account required." }, { status: 403 });
  }

  const body = await request.json();
  const { name, address, timezone } = body;

  if (!name) {
    return NextResponse.json({ detail: "name required" }, { status: 400 });
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("partner_venues")
    .insert({
      partner_id: partnerId,
      name,
      address: address ?? null,
      timezone: timezone ?? "UTC",
      is_active: true,
    })
    .select("id")
    .single();

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ id: data.id });
}
