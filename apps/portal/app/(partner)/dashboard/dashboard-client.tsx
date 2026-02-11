"use client";

import Link from "next/link";

type DashboardStats = {
  ordersToday: number;
  earnings: number;
  alerts: number;
  pendingOrders: number;
  lowStockCount: number;
  activeConversations: number;
  unassignedConversations: number;
  productHealth: {
    totalProducts: number;
    lowStockCount: number;
    productsWithIssues: { id: string; name: string; issue: string }[];
  };
  trendingProducts: { id: string; name: string; orderCount: number }[];
  cartSummary: {
    totalItems: number;
    uniqueProducts: number;
    products: { id: string; name: string }[];
  };
  ratings: { avgRating: number; totalReviews: number };
};

export function DashboardClient({ stats }: { stats: DashboardStats }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <Link href="/orders">
          <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))] hover:border-[rgb(var(--color-primary))] transition cursor-pointer">
            <p className="text-[rgb(var(--color-text-secondary))]">Orders Today</p>
            <p className="text-2xl font-semibold">{stats.ordersToday}</p>
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">View orders →</p>
          </div>
        </Link>
        <Link href="/earnings">
          <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))] hover:border-[rgb(var(--color-primary))] transition cursor-pointer">
            <p className="text-[rgb(var(--color-text-secondary))]">Earnings</p>
            <p className="text-2xl font-semibold">${stats.earnings.toLocaleString()}</p>
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">View earnings →</p>
          </div>
        </Link>
        <Link href="/orders">
          <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))] hover:border-[rgb(var(--color-primary))] transition cursor-pointer">
            <p className="text-[rgb(var(--color-text-secondary))]">Alerts</p>
            <p className="text-2xl font-semibold">{stats.alerts}</p>
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
              {stats.pendingOrders} pending · {stats.lowStockCount} low stock
            </p>
          </div>
        </Link>
        <Link href="/ratings">
          <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))] hover:border-[rgb(var(--color-primary))] transition cursor-pointer">
            <p className="text-[rgb(var(--color-text-secondary))]">Ratings</p>
            <p className="text-2xl font-semibold">{stats.ratings.avgRating.toFixed(1)} ★</p>
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
              {stats.ratings.totalReviews} reviews · View ratings →
            </p>
          </div>
        </Link>
        <Link href="/conversations">
          <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))] hover:border-[rgb(var(--color-primary))] transition cursor-pointer">
            <p className="text-[rgb(var(--color-text-secondary))]">Conversations</p>
            <p className="text-2xl font-semibold">{stats.activeConversations}</p>
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
              {stats.unassignedConversations} unassigned · View conversations →
            </p>
          </div>
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Product Health</h2>
            <Link href="/products" className="text-sm text-[rgb(var(--color-primary))] hover:underline">
              View products →
            </Link>
          </div>
          <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">
            {stats.productHealth.totalProducts} products · {stats.productHealth.lowStockCount} need attention
          </p>
          {stats.productHealth.productsWithIssues.length > 0 ? (
            <ul className="space-y-2">
              {stats.productHealth.productsWithIssues.map((p) => (
                <li key={p.id} className="flex justify-between text-sm">
                  <Link href={`/products/${p.id}`} className="hover:underline">
                    {p.name}
                  </Link>
                  <span className="text-amber-600">{p.issue}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-green-600">All products healthy</p>
          )}
        </div>

        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Trending in Orders</h2>
            <Link href="/analytics" className="text-sm text-[rgb(var(--color-primary))] hover:underline">
              View analytics →
            </Link>
          </div>
          <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">
            Most ordered this week
          </p>
          {stats.trendingProducts.length > 0 ? (
            <ul className="space-y-2">
              {stats.trendingProducts.map((p) => (
                <li key={p.id} className="flex justify-between text-sm">
                  <Link href={`/products/${p.id}`} className="hover:underline">
                    {p.name}
                  </Link>
                  <span>{p.orderCount} orders</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-[rgb(var(--color-text-secondary))]">No orders yet</p>
          )}
        </div>
      </div>

      <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Products in Cart</h2>
          <span className="text-sm text-[rgb(var(--color-text-secondary))]">
            {stats.cartSummary.totalItems} items · {stats.cartSummary.uniqueProducts} products
          </span>
        </div>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">
          Your products currently in customer carts (draft bundles)
        </p>
        {stats.cartSummary.products.length > 0 ? (
          <ul className="space-y-2">
            {stats.cartSummary.products.map((p) => (
              <li key={p.id}>
                <Link href={`/products/${p.id}`} className="text-sm hover:underline">
                  {p.name}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-[rgb(var(--color-text-secondary))]">No products in cart</p>
        )}
      </div>
    </div>
  );
}
