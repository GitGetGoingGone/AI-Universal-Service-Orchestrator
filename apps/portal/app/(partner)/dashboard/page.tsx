import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { getPartnerId } from "@/lib/auth";
import { createSupabaseServerClient } from "@/lib/supabase";

async function getDashboardStats(partnerId: string) {
  const supabase = createSupabaseServerClient();

  const now = new Date();
  const todayStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const todayEnd = new Date(todayStart);
  todayEnd.setUTCDate(todayEnd.getUTCDate() + 1);
  const todayStartStr = todayStart.toISOString();
  const todayEndStr = todayEnd.toISOString();

  const [{ count: ordersToday }, { data: earningsRows }, { data: products }] = await Promise.all([
    supabase
      .from("order_legs")
      .select("id", { count: "exact", head: true })
      .eq("partner_id", partnerId)
      .gte("created_at", todayStartStr)
      .lt("created_at", todayEndStr),
    supabase
      .from("order_items")
      .select("total_price, orders(status)")
      .eq("partner_id", partnerId),
    supabase
      .from("products")
      .select("id")
      .eq("partner_id", partnerId)
      .is("deleted_at", null),
  ]);

  const completedStatuses = ["completed", "paid"];
  const earningsTotal =
    earningsRows
      ?.filter((r) => {
        const order = r.orders as { status?: string } | null;
        return order && completedStatuses.includes(order.status ?? "");
      })
      .reduce((sum, r) => sum + Number(r.total_price ?? 0), 0) ?? 0;

  const productIds = (products ?? []).map((p) => p.id);
  let lowStockCount = 0;
  if (productIds.length > 0) {
    const { data: inv } = await supabase
      .from("product_inventory")
      .select("quantity, low_stock_threshold")
      .in("product_id", productIds);
    lowStockCount =
      inv?.filter((i) => (i.quantity ?? 0) <= (i.low_stock_threshold ?? 5)).length ?? 0;
  }

  const { count: pendingOrders } = await supabase
    .from("order_legs")
    .select("id", { count: "exact", head: true })
    .eq("partner_id", partnerId)
    .eq("status", "pending");

  return {
    ordersToday: ordersToday ?? 0,
    earnings: Number(earningsTotal.toFixed(2)),
    alerts: lowStockCount + (pendingOrders ?? 0),
  };
}

export default async function DashboardPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  const partnerId = await getPartnerId();
  const stats = partnerId ? await getDashboardStats(partnerId) : { ordersToday: 0, earnings: 0, alerts: 0 };

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Orders Today</p>
          <p className="text-2xl font-semibold">{stats.ordersToday}</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Earnings</p>
          <p className="text-2xl font-semibold">${stats.earnings.toLocaleString()}</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Alerts</p>
          <p className="text-2xl font-semibold">{stats.alerts}</p>
        </div>
      </div>
    </main>
  );
}
