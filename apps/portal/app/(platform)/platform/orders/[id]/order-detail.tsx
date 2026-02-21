"use client";

import { useEffect, useState } from "react";

type FulfillmentDetails = {
  pickup_time?: string;
  pickup_address?: string;
  delivery_address?: string;
  [key: string]: unknown;
};

type OrderItem = {
  id: string;
  item_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
};

type Order = {
  id: string;
  bundle_id: string | null;
  user_id: string | null;
  total_amount: number;
  currency: string;
  status: string;
  payment_status: string;
  created_at: string;
  paid_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  customer_name: string | null;
  customer_email: string | null;
  customer_phone: string | null;
  fulfillment_details: FulfillmentDetails | null;
  items: OrderItem[];
};

export function OrderDetail({ orderId }: { orderId: string }) {
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await fetch(`/api/platform/orders/${orderId}`);
        if (!res.ok) {
          if (res.status === 404) setError("Order not found");
          else setError("Failed to load order");
          return;
        }
        const data = await res.json();
        if (!cancelled) setOrder(data.order);
      } catch {
        if (!cancelled) setError("Failed to load order");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [orderId]);

  if (loading) {
    return <p className="text-[rgb(var(--color-text-secondary))]">Loading order…</p>;
  }
  if (error || !order) {
    return <p className="text-red-600">{error ?? "Order not found"}</p>;
  }

  const fd = order.fulfillment_details ?? {};
  const addr = (v: unknown) => (typeof v === "string" ? v : Array.isArray(v) ? v.join(", ") : v != null ? String(v) : "—");

  return (
    <div className="space-y-8">
      <section className="border border-[rgb(var(--color-border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Order</h2>
        <dl className="grid gap-2 text-sm">
          <div>
            <dt className="text-[rgb(var(--color-text-secondary))]">Order ID</dt>
            <dd className="font-mono" title={order.id}>{order.id}</dd>
          </div>
          <div>
            <dt className="text-[rgb(var(--color-text-secondary))]">Bundle ID</dt>
            <dd className="font-mono">{order.bundle_id ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-[rgb(var(--color-text-secondary))]">Status</dt>
            <dd>
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${
                  order.status === "completed"
                    ? "bg-green-500/20 text-green-700 dark:text-green-400"
                    : order.status === "cancelled"
                      ? "bg-red-500/20 text-red-700 dark:text-red-400"
                      : "bg-amber-500/20 text-amber-700 dark:text-amber-400"
                }`}
              >
                {order.status}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-[rgb(var(--color-text-secondary))]">Payment</dt>
            <dd>
              <span
                className={`px-2 py-0.5 rounded text-xs font-medium ${
                  order.payment_status === "paid"
                    ? "bg-green-500/20 text-green-700 dark:text-green-400"
                    : "bg-[rgb(var(--color-border))]/50"
                }`}
              >
                {order.payment_status}
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-[rgb(var(--color-text-secondary))]">Total</dt>
            <dd className="font-medium">{order.currency} {Number(order.total_amount).toFixed(2)}</dd>
          </div>
          <div>
            <dt className="text-[rgb(var(--color-text-secondary))]">Placed</dt>
            <dd>{new Date(order.created_at).toLocaleString()}</dd>
          </div>
        </dl>
      </section>

      <section className="border border-[rgb(var(--color-border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Customer</h2>
        <dl className="grid gap-2 text-sm">
          <div>
            <dt className="text-[rgb(var(--color-text-secondary))]">Name</dt>
            <dd>{order.customer_name ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-[rgb(var(--color-text-secondary))]">Email</dt>
            <dd>
              {order.customer_email ? (
                <a href={`mailto:${order.customer_email}`} className="text-[rgb(var(--color-primary))] hover:underline">
                  {order.customer_email}
                </a>
              ) : (
                "—"
              )}
            </dd>
          </div>
          <div>
            <dt className="text-[rgb(var(--color-text-secondary))]">Phone</dt>
            <dd>
              {order.customer_phone ? (
                <a href={`tel:${order.customer_phone}`} className="text-[rgb(var(--color-primary))] hover:underline">
                  {order.customer_phone}
                </a>
              ) : (
                "—"
              )}
            </dd>
          </div>
        </dl>
      </section>

      {(fd.pickup_address || fd.delivery_address || fd.pickup_time) && (
        <section className="border border-[rgb(var(--color-border))] rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Address &amp; fulfillment</h2>
          <dl className="grid gap-2 text-sm">
            {fd.pickup_time != null && (
              <div>
                <dt className="text-[rgb(var(--color-text-secondary))]">Pickup time</dt>
                <dd>{addr(fd.pickup_time)}</dd>
              </div>
            )}
            {fd.pickup_address != null && (
              <div>
                <dt className="text-[rgb(var(--color-text-secondary))]">Pickup address</dt>
                <dd className="whitespace-pre-wrap">{addr(fd.pickup_address)}</dd>
              </div>
            )}
            {fd.delivery_address != null && (
              <div>
                <dt className="text-[rgb(var(--color-text-secondary))]">Delivery address</dt>
                <dd className="whitespace-pre-wrap">{addr(fd.delivery_address)}</dd>
              </div>
            )}
          </dl>
        </section>
      )}

      <section className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <h2 className="text-lg font-semibold px-6 py-4 border-b border-[rgb(var(--color-border))]">Line items</h2>
        <table className="w-full">
          <thead className="bg-[rgb(var(--color-surface))]">
            <tr>
              <th className="text-left px-4 py-2">Item</th>
              <th className="text-right px-4 py-2">Qty</th>
              <th className="text-right px-4 py-2">Unit price</th>
              <th className="text-right px-4 py-2">Total</th>
            </tr>
          </thead>
          <tbody>
            {(order.items ?? []).map((item) => (
              <tr key={item.id} className="border-t border-[rgb(var(--color-border))]">
                <td className="px-4 py-2">{item.item_name}</td>
                <td className="px-4 py-2 text-right">{item.quantity}</td>
                <td className="px-4 py-2 text-right">{order.currency} {Number(item.unit_price).toFixed(2)}</td>
                <td className="px-4 py-2 text-right">{order.currency} {Number(item.total_price).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!order.items || order.items.length === 0) && (
          <p className="px-4 py-6 text-center text-[rgb(var(--color-text-secondary))] text-sm">No line items</p>
        )}
      </section>
    </div>
  );
}
