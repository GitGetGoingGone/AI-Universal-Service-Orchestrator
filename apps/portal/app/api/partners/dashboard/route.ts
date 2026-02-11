import { NextResponse } from "next/server";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

export async function GET() {
  const partnerId = await getPartnerId();
  if (!partnerId) {
    return NextResponse.json({ detail: "No partner account" }, { status: 403 });
  }

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

  // Orders today, earnings, pending orders
  const [{ count: ordersToday }, { data: orderItemsData }, { count: pendingOrders }, { data: products }] =
    await Promise.all([
      supabase
        .from("order_legs")
        .select("id", { count: "exact", head: true })
        .eq("partner_id", partnerId)
        .gte("created_at", todayStartStr)
        .lt("created_at", todayEndStr),
      supabase
        .from("order_items")
        .select("total_price, product_id, orders(status)")
        .eq("partner_id", partnerId)
        .gte("created_at", weekStartStr),
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
    ]);

  const completedStatuses = ["completed", "paid"];
  const earningsTotal =
    (orderItemsData as { total_price?: number; orders?: { status?: string } }[] | null)
      ?.filter((r) => {
        const order = r.orders as { status?: string } | null;
        return order && completedStatuses.includes(order.status ?? "");
      })
      .reduce((sum, r) => sum + Number(r.total_price ?? 0), 0) ?? 0;

  // Product health: low stock count
  const productIds = (products ?? []).map((p) => p.id);
  let lowStockCount = 0;
  let productsWithIssues: { id: string; name: string; issue: string }[] = [];
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

  // Trending: most ordered products (last 7 days)
  const productOrderCounts: Record<string, { count: number; name: string }> = {};
  (orderItemsData as { product_id?: string; total_price?: number; orders?: { status?: string } }[] | null)
    ?.filter((r) => {
      const order = r.orders as { status?: string } | null;
      return order && completedStatuses.includes(order.status ?? "");
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

  // Products in cart (bundle_legs where bundle status = draft)
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
      ? await supabase
          .from("products")
          .select("id, name")
          .in("id", cartProductIds)
      : { data: [] };
  const cartCount = inCartBundles.length;
  const cartProductsList = (cartProducts ?? []).map((p) => ({
    id: p.id,
    name: (p as { name?: string }).name ?? "Unknown",
  }));

  const { count: activeConversations } = await supabase
    .from("conversations")
    .select("id", { count: "exact", head: true })
    .eq("partner_id", partnerId)
    .eq("status", "active");

  const { count: unassignedConversations } = await supabase
    .from("conversations")
    .select("id", { count: "exact", head: true })
    .eq("partner_id", partnerId)
    .eq("status", "active")
    .is("assigned_to_member_id", null);

  const { data: ratings } = await supabase
    .from("partner_ratings")
    .select("avg_rating, total_reviews")
    .eq("partner_id", partnerId)
    .single();

  return NextResponse.json({
    ordersToday: ordersToday ?? 0,
    earnings: Number(earningsTotal.toFixed(2)),
    alerts: lowStockCount + (pendingOrders ?? 0),
    pendingOrders: pendingOrders ?? 0,
    lowStockCount,
    activeConversations: activeConversations ?? 0,
    unassignedConversations: unassignedConversations ?? 0,
    ratings: {
      avgRating: (ratings as { avg_rating?: number } | null)?.avg_rating ?? 0,
      totalReviews: (ratings as { total_reviews?: number } | null)?.total_reviews ?? 0,
    },
    productHealth: {
      totalProducts: productIds.length,
      lowStockCount,
      productsWithIssues: productsWithIssues.slice(0, 5),
    },
    trendingProducts,
    cartSummary: {
      totalItems: cartCount,
      uniqueProducts: cartProductsList.length,
      products: cartProductsList,
    },
  });
}
