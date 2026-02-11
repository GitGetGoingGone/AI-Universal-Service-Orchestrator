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
  else start.setFullYear(start.getFullYear() - 1);
  const startStr = start.toISOString();

  const { data: orderLegs } = await supabase
    .from("order_legs")
    .select("id, created_at, orders(total_amount)")
    .eq("partner_id", partnerId)
    .gte("created_at", startStr)
    .order("created_at", { ascending: true });

  const { data: orderItemsRaw } = await supabase
    .from("order_items")
    .select("product_id, quantity, total_price, orders(status, created_at)")
    .eq("partner_id", partnerId);
  const orderItems = (orderItemsRaw ?? []).filter((r) => {
    const o = r.orders as { created_at?: string } | null;
    return o?.created_at && o.created_at >= startStr;
  });

  const completedStatuses = ["completed", "paid"];
  const byHour: Record<number, number> = {};
  for (let h = 0; h < 24; h++) byHour[h] = 0;
  (orderLegs ?? []).forEach((leg) => {
    const d = new Date(leg.created_at);
    byHour[d.getHours()]++;
  });

  const peakHours = Object.entries(byHour)
    .map(([h, c]) => ({ hour: parseInt(h, 10), count: c }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  const productCounts: Record<string, { count: number; revenue: number; name?: string }> = {};
  (orderItems ?? []).forEach((r) => {
    const o = r.orders as { status?: string } | null;
    if (!o || !completedStatuses.includes(o.status ?? "")) return;
    const pid = r.product_id ?? "";
    if (!pid) return;
    productCounts[pid] = {
      count: (productCounts[pid]?.count ?? 0) + (r.quantity ?? 1),
      revenue: (productCounts[pid]?.revenue ?? 0) + Number(r.total_price ?? 0),
    };
  });

  const productIds = Object.keys(productCounts);
  const { data: products } =
    productIds.length > 0
      ? await supabase.from("products").select("id, name").in("id", productIds)
      : { data: [] };
  const productMap = new Map((products ?? []).map((p) => [p.id, (p as { name?: string }).name]));
  const popularItems = Object.entries(productCounts)
    .map(([id, v]) => ({
      id,
      name: productMap.get(id) ?? "Unknown",
      orderCount: v.count,
      revenue: v.revenue,
    }))
    .sort((a, b) => b.orderCount - a.orderCount)
    .slice(0, 10);

  const salesByDay: Record<string, number> = {};
  (orderLegs ?? []).forEach((leg) => {
    const d = new Date(leg.created_at);
    const key = d.toISOString().slice(0, 10);
    const amt = (leg.orders as { total_amount?: number })?.total_amount ?? 0;
    salesByDay[key] = (salesByDay[key] ?? 0) + Number(amt);
  });
  const salesData = Object.entries(salesByDay)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([date, revenue]) => ({ date, revenue }));

  return NextResponse.json({
    period,
    salesByDay: salesData,
    peakHours,
    popularItems,
    totalOrders: orderLegs?.length ?? 0,
  });
}
