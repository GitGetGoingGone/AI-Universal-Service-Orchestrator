"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Order = {
  id: string;
  bundle_id: string | null;
  user_id: string | null;
  total_amount: number;
  currency: string;
  status: string;
  payment_status: string;
  created_at: string;
  item_count?: number;
  customer_name?: string | null;
  customer_email?: string | null;
  customer_phone?: string | null;
};

export function OrdersList() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  async function fetchOrders() {
    setLoading(true);
    try {
      const res = await fetch("/api/platform/orders?limit=100");
      if (!res.ok) throw new Error("Failed to load orders");
      const data = await res.json();
      setOrders(data.orders ?? []);
    } catch {
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchOrders();
  }, []);

  if (loading) {
    return <p className="text-[rgb(var(--color-text-secondary))]">Loading orders...</p>;
  }

  return (
    <div className="space-y-4">
      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-x-auto">
        <table className="w-full min-w-[900px]">
          <thead className="bg-[rgb(var(--color-surface))]">
            <tr>
              <th className="text-left px-4 py-2">Order</th>
              <th className="text-left px-4 py-2">Name</th>
              <th className="text-left px-4 py-2">Email</th>
              <th className="text-left px-4 py-2">Phone</th>
              <th className="text-left px-4 py-2">Total</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Payment</th>
              <th className="text-left px-4 py-2">Items</th>
              <th className="text-left px-4 py-2">Placed</th>
              <th className="text-left px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id} className="border-t border-[rgb(var(--color-border))]">
                <td className="px-4 py-2 font-mono text-sm" title={o.id}>
                  {o.id.slice(0, 8)}…
                </td>
                <td className="px-4 py-2 text-sm">{o.customer_name ?? "—"}</td>
                <td className="px-4 py-2 text-sm">
                  {o.customer_email ? (
                    <a href={`mailto:${o.customer_email}`} className="text-[rgb(var(--color-primary))] hover:underline">
                      {o.customer_email}
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-4 py-2 text-sm">
                  {o.customer_phone ? (
                    <a href={`tel:${o.customer_phone}`} className="text-[rgb(var(--color-primary))] hover:underline">
                      {o.customer_phone}
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-4 py-2">
                  {o.currency} {Number(o.total_amount).toFixed(2)}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      o.status === "completed"
                        ? "bg-green-500/20 text-green-700 dark:text-green-400"
                        : o.status === "cancelled"
                          ? "bg-red-500/20 text-red-700 dark:text-red-400"
                          : "bg-amber-500/20 text-amber-700 dark:text-amber-400"
                    }`}
                  >
                    {o.status}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs ${
                      o.payment_status === "paid"
                        ? "bg-green-500/20 text-green-700 dark:text-green-400"
                        : "bg-[rgb(var(--color-border))]/50"
                    }`}
                  >
                    {o.payment_status}
                  </span>
                </td>
                <td className="px-4 py-2">{o.item_count ?? "—"}</td>
                <td className="px-4 py-2 text-[rgb(var(--color-text-secondary))] text-sm whitespace-nowrap">
                  {new Date(o.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-2">
                  <Link
                    href={`/platform/orders/${o.id}`}
                    className="text-sm text-[rgb(var(--color-primary))] hover:underline font-medium"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {orders.length === 0 && (
          <p className="px-4 py-8 text-center text-[rgb(var(--color-text-secondary))]">
            No orders yet.
          </p>
        )}
      </div>
    </div>
  );
}
