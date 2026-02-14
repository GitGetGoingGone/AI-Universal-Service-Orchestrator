import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  try {
    const partnerId = await getPartnerId();
    if (!partnerId) {
      return NextResponse.json({ detail: "No partner account" }, { status: 403 });
    }

    const supabase = createSupabaseServerClient();
    const { data, error } = await supabase
      .from("product_sponsorships")
      .select("id, product_id, start_at, end_at, amount_cents, currency, status, created_at")
      .eq("partner_id", partnerId)
      .order("created_at", { ascending: false });

    if (error) {
      return NextResponse.json({ detail: error.message }, { status: 500 });
    }

    return NextResponse.json({ sponsorships: data ?? [] });
  } catch (err) {
    return NextResponse.json(
      { detail: err instanceof Error ? err.message : "Internal server error" },
      { status: 500 }
    );
  }
}
