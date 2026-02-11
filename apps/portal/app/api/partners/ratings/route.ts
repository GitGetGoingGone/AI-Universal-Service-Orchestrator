import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const supabase = createSupabaseServerClient();
  const { data: summary } = await supabase
    .from("partner_ratings")
    .select("avg_rating, total_reviews")
    .eq("partner_id", partnerId)
    .single();

  const { data: reviews } = await supabase
    .from("order_reviews")
    .select("id, order_id, rating, comment, partner_response, responded_at, created_at")
    .eq("partner_id", partnerId)
    .order("created_at", { ascending: false })
    .limit(50);

  return NextResponse.json({
    avgRating: summary?.avg_rating ?? 0,
    totalReviews: summary?.total_reviews ?? 0,
    reviews: reviews ?? [],
  });
}
