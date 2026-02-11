import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";
import { DashboardClient } from "./dashboard-client";

async function getDashboardStats(partnerId: string) {
  const supabase = createSupabaseServerClient();
  const now = new Date();
  const todayStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const todayEnd = new Date(todayStart);
  todayEnd.setUTCDate(todayEnd.getUTCDate() + 1);
  const weekStart = new Date(todayStart);
  weekStart.setUTCDate(weekStart.getUTCDate() - 7);
  const todayStartStr = todayStart.toISOString();
  const todayEndStr = todayEnd.toISOString();
  const weekStartStr = weekStart.toISOString();

  const [
    { count: ordersToday },
    { data: orderItemsData },
    { count: pendingOrders },
    { data: products },
    { data: ratings },
    { count: activeConversations },
    { count: unassignedConversations },
  ] = await Promise.all([
      supabase
        .from("order_legs")
        .select("id", { count: "exact", head: true })
        .eq("partner_id", partnerId)
        .gte("created_at", todayStartStr)
        .lt("created_at", todayEndStr),
      supabase
        .from("order_items")
        .select("total_price, product_id, orders(status, created_at)")
        .eq("partner_id", partnerId),
      supabase
        .from("order_legs")
        .select("id", { count: "exact", head: true })
        .eq("partner_id", partnerId)
        .eq("status", "pending"),
      supabase
        .from("products")
        .select("id, name")
        .eq("partner_id", partnerId)
        .is("deleted_at", null),
      supabase
        .from("partner_ratings")
        .select("avg_rating, total_reviews")
        .eq("partner_id", partnerId)
        .single(),
      supabase
        .from("conversations")
        .select("id", { count: "exact", head: true })
        .eq("partner_id", partnerId)
        .eq("status", "active"),
      supabase
        .from("conversations")
        .select("id", { count: "exact", head: true })
        .eq("partner_id", partnerId)
        .eq("status", "active")
        .is("assigned_to_member_id", null),
    ]);

  const completedStatuses = ["completed", "paid"];
  const earningsTotal =
    (orderItemsData as { total_price?: number; orders?: { status?: string } }[] | null)
      ?.filter((r) => {
        const o = r.orders as { status?: string } | null;
        return o && completedStatuses.includes(o.status ?? "");
      })
      .reduce((sum, r) => sum + Number(r.total_price ?? 0), 0) ?? 0;

  const productIds = (products ?? []).map((p) => p.id);
  let lowStockCount = 0;
  const productsWithIssues: { id: string; name: string; issue: string }[] = [];
  if (productIds.length > 0) {
    const { data: inv } = await supabase
      .from("product_inventory")
      .select("product_id, quantity, low_stock_threshold")
      .in("product_id", productIds);
    inv?.forEach((i) => {
      const qty = i.quantity ?? 0;
      const threshold = i.low_stock_threshold ?? 5;
      if (qty <= threshold) {
        lowStockCount++;
        const p = products?.find((x) => x.id === i.product_id);
        productsWithIssues.push({
          id: i.product_id,
          name: (p as { name?: string })?.name ?? "Unknown",
          issue: qty === 0 ? "Out of stock" : "Low stock",
        });
      }
    });
  }

  const productOrderCounts: Record<string, { count: number; name: string }> = {};
  (orderItemsData as { product_id?: string; orders?: { status?: string; created_at?: string } }[] | null)
    ?.filter((r) => {
      const o = r.orders as { status?: string; created_at?: string } | null;
      if (!o || !completedStatuses.includes(o.status ?? "")) return false;
      const createdAt = o.created_at ? new Date(o.created_at).getTime() : 0;
      return createdAt >= weekStart.getTime();
    })
    .forEach((r) => {
      const pid = r.product_id ?? "";
      if (!pid) return;
      const p = products?.find((x) => x.id === pid) as { name?: string } | undefined;
      productOrderCounts[pid] = {
        count: (productOrderCounts[pid]?.count ?? 0) + 1,
        name: p?.name ?? "Unknown",
      };
    });
  const trendingProducts = Object.entries(productOrderCounts)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 5)
    .map(([id, v]) => ({ id, name: v.name, orderCount: v.count }));

  const { data: bundleLegs } = await supabase
    .from("bundle_legs")
    .select("id, product_id, bundle_id")
    .eq("partner_id", partnerId);
  const bundleIds = [...new Set((bundleLegs ?? []).map((bl) => bl.bundle_id).filter(Boolean))];
  const { data: bundlesData } =
    bundleIds.length > 0
      ? await supabase.from("bundles").select("id, status").in("id", bundleIds)
      : { data: [] };
  const draftBundleIds = new Set(
    (bundlesData ?? []).filter((b) => (b as { status?: string }).status === "draft").map((b) => b.id)
  );
  const inCartBundles = (bundleLegs ?? []).filter((bl) => draftBundleIds.has(bl.bundle_id));
  const cartProductIds = [...new Set(inCartBundles.map((bl) => bl.product_id).filter(Boolean))];
  const { data: cartProducts } =
    cartProductIds.length > 0
      ? await supabase.from("products").select("id, name").in("id", cartProductIds)
      : { data: [] };
  const cartProductsList = (cartProducts ?? []).map((p) => ({
    id: p.id,
    name: (p as { name?: string }).name ?? "Unknown",
  }));

  return {
    ordersToday: ordersToday ?? 0,
    earnings: Number(earningsTotal.toFixed(2)),
    alerts: lowStockCount + (pendingOrders ?? 0),
    pendingOrders: pendingOrders ?? 0,
    lowStockCount,
    productHealth: {
      totalProducts: productIds.length,
      lowStockCount,
      productsWithIssues: productsWithIssues.slice(0, 5),
    },
    trendingProducts,
    cartSummary: {
      totalItems: inCartBundles.length,
      uniqueProducts: cartProductsList.length,
      products: cartProductsList,
    },
    ratings: {
      avgRating: (ratings as { avg_rating?: number } | null)?.avg_rating ?? 0,
      totalReviews: (ratings as { total_reviews?: number } | null)?.total_reviews ?? 0,
    },
    activeConversations: activeConversations ?? 0,
    unassignedConversations: unassignedConversations ?? 0,
  };
}

export default async function DashboardPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  const partnerId = await getPartnerId();
  const defaultStats = {
    ordersToday: 0,
    earnings: 0,
    alerts: 0,
    pendingOrders: 0,
    lowStockCount: 0,
    activeConversations: 0,
    unassignedConversations: 0,
    productHealth: { totalProducts: 0, lowStockCount: 0, productsWithIssues: [] },
    trendingProducts: [],
    cartSummary: { totalItems: 0, uniqueProducts: 0, products: [] },
    ratings: { avgRating: 0, totalReviews: 0 },
  };
  const stats = partnerId
    ? await getDashboardStats(partnerId).catch(() => defaultStats)
    : defaultStats;

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <DashboardClient stats={stats} />
    </main>
  );
}
