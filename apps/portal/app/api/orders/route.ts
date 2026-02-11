import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const supabase = createSupabaseServerClient();
  const { data, error } = await supabase
    .from("order_legs")
    .select(`
      id,
      status,
      preparation_mins,
      reject_reason,
      created_at,
      orders (
        id,
        total_amount,
        currency,
        status,
        payment_status,
        created_at
      )
    `)
    .eq("partner_id", partnerId)
    .order("created_at", { ascending: false })
    .limit(50);

  if (error) {
    return NextResponse.json({ detail: error.message }, { status: 500 });
  }

  return NextResponse.json({ orders: data ?? [] });
}
