"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";

type OrderLeg = {
  id: string;
  status: string;
  preparation_mins: number | null;
  reject_reason: string | null;
  created_at: string;
  orders: { id: string; total_amount: number; currency: string; status: string; created_at: string } | null;
};

export function OrderQueue() {
  const [orders, setOrders] = useState<OrderLeg[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchOrders() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/orders");
      if (res.status === 403) {
        setError("PARTNER_REQUIRED");
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to load");
      }
      const data = await res.json();
      setOrders(data.orders ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchOrders();
  }, []);

  async function accept(id: string, prepMins: number) {
    try {
      const res = await fetch(`/api/orders/${id}/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preparation_mins: prepMins }),
      });
      if (!res.ok) throw new Error("Failed");
      fetchOrders();
    } catch {
      setError("Failed to accept");
    }
  }

  async function reject(id: string, reason: string) {
    try {
      const res = await fetch(`/api/orders/${id}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      if (!res.ok) throw new Error("Failed");
      fetchOrders();
    } catch {
      setError("Failed to reject");
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (error === "PARTNER_REQUIRED") return <PartnerRequiredMessage />;
  if (error) return <p className="text-[rgb(var(--color-error))]">{error}</p>;

  const pending = orders.filter((o) => o.status === "pending");
  const other = orders.filter((o) => o.status !== "pending");

  return (
    <PartnerGuard>
    <div className="space-y-6">
      {pending.length > 0 && (
        <div>
          <h2 className="font-semibold mb-2">Pending ({pending.length})</h2>
          <div className="space-y-2">
            {pending.map((leg) => (
              <OrderCard
                key={leg.id}
                leg={leg}
                onAccept={(prep) => accept(leg.id, prep)}
                onReject={(reason) => reject(leg.id, reason)}
              />
            ))}
          </div>
        </div>
      )}

      <div>
        <h2 className="font-semibold mb-2">All Orders</h2>
        <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-[rgb(var(--color-surface))]">
              <tr>
                <th className="text-left px-4 py-2">Order</th>
                <th className="text-left px-4 py-2">Amount</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="text-left px-4 py-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((leg) => (
                <tr key={leg.id} className="border-t border-[rgb(var(--color-border))]">
                  <td className="px-4 py-2">{leg.orders?.id?.slice(0, 8) ?? leg.id.slice(0, 8)}...</td>
                  <td className="px-4 py-2">
                    {leg.orders?.currency ?? "USD"} {Number(leg.orders?.total_amount ?? 0).toFixed(2)}
                  </td>
                  <td className="px-4 py-2">{leg.status}</td>
                  <td className="px-4 py-2">
                    {leg.created_at ? new Date(leg.created_at).toLocaleString() : "—"}
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
    </div>
    </PartnerGuard>
  );
}

function OrderCard({
  leg,
  onAccept,
  onReject,
}: {
  leg: OrderLeg;
  onAccept: (prepMins: number) => void;
  onReject: (reason: string) => void;
}) {
  const [prep, setPrep] = useState(15);
  const [rejectReason, setRejectReason] = useState("");

  return (
    <div className="p-4 border border-[rgb(var(--color-border))] rounded-lg bg-[rgb(var(--color-surface))]">
      <p className="font-medium">
        Order {leg.orders?.id?.slice(0, 8) ?? leg.id.slice(0, 8)}... — {leg.orders?.currency ?? "USD"}{" "}
        {Number(leg.orders?.total_amount ?? 0).toFixed(2)}
      </p>
      <p className="text-sm text-[rgb(var(--color-text-secondary))]">
        {leg.created_at ? new Date(leg.created_at).toLocaleString() : ""}
      </p>
      <div className="mt-3 flex flex-wrap gap-2 items-center">
        <label className="flex items-center gap-2">
          <span className="text-sm">Prep (min):</span>
          <input
            type="number"
            min="0"
            value={prep}
            onChange={(e) => setPrep(Number(e.target.value))}
            className="w-16 px-2 py-1 rounded border border-[rgb(var(--color-border))]"
          />
        </label>
        <Button size="sm" onClick={() => onAccept(prep)}>
          Accept
        </Button>
        <input
          type="text"
          placeholder="Reject reason"
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          className="px-2 py-1 rounded border border-[rgb(var(--color-border))] w-40"
        />
        <Button size="sm" variant="destructive" onClick={() => onReject(rejectReason || "Rejected")}>
          Reject
        </Button>
      </div>
    </div>
  );
}
