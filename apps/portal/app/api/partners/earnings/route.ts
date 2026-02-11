import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET(request: Request) {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

  const supabase = createSupabaseServerClient();
  const { searchParams } = new URL(request.url);
  const period = searchParams.get("period") || "30d";
  const now = new Date();
  const start = new Date(now);
  if (period === "7d") start.setDate(start.getDate() - 7);
  else if (period === "30d") start.setDate(start.getDate() - 30);
  else if (period === "90d") start.setDate(start.getDate() - 90);
  else start.setFullYear(start.getFullYear() - 1);
  const startStr = start.toISOString();

  const { data: orderItems } = await supabase
    .from("order_items")
    .select("total_price, quantity, unit_price, orders(id, status, created_at)")
    .eq("partner_id", partnerId)
    .order("created_at", { ascending: false });

  const completedStatuses = ["completed", "paid"];
  const filtered = (orderItems ?? []).filter((r) => {
    const o = r.orders as { status?: string; created_at?: string } | null;
    return o && completedStatuses.includes(o.status ?? "") && (o.created_at ?? "") >= startStr;
  });

  const totalEarnings = filtered.reduce((s, r) => s + Number(r.total_price ?? 0), 0);

  const { data: commissionBreaks } = await supabase
    .from("commission_breaks")
    .select("gross_cents, commission_cents, net_cents, created_at")
    .eq("partner_id", partnerId)
    .gte("created_at", startStr)
    .order("created_at", { ascending: false });

  const { data: payouts } = await supabase
    .from("payouts")
    .select("id, amount_cents, fee_cents, status, settled_at, created_at")
    .eq("partner_id", partnerId)
    .order("created_at", { ascending: false })
    .limit(50);

  const totalPayouts = (payouts ?? []).reduce((s, p) => s + (p.amount_cents ?? 0), 0) / 100;
  const totalCommission = (commissionBreaks ?? []).reduce((s, c) => s + (c.commission_cents ?? 0), 0) / 100;

  return NextResponse.json({
    period,
    totalEarnings: Number(totalEarnings.toFixed(2)),
    totalCommission,
    totalPayouts,
    commissionBreaks: commissionBreaks ?? [],
    payouts: payouts ?? [],
    orderCount: filtered.length,
  });
}
