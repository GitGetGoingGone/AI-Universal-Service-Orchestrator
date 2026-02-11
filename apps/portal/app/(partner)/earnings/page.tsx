"use client";

import { useEffect, useState } from "react";

type Payout = {
  id: string;
  amount_cents: number;
  fee_cents: number;
  status: string;
  settled_at: string | null;
  created_at: string;
};

type CommissionBreak = {
  gross_cents: number;
  commission_cents: number;
  net_cents: number;
  created_at: string;
};

type EarningsData = {
  period: string;
  totalEarnings: number;
  totalCommission: number;
  totalPayouts: number;
  commissionBreaks: CommissionBreak[];
  payouts: Payout[];
  orderCount: number;
};

export default function EarningsPage() {
  const [data, setData] = useState<EarningsData | null>(null);
  const [period, setPeriod] = useState("30d");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/partners/earnings?period=${period}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.detail) throw new Error(d.detail);
        setData(d);
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [period]);

  if (loading) return <p className="p-6">Loading…</p>;
  if (!data) return <p className="p-6 text-red-600">Failed to load earnings</p>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Earnings</h1>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="rounded border border-[rgb(var(--color-border))] px-3 py-2 bg-[rgb(var(--color-background))]"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="all">All time</option>
        </select>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Gross Earnings</p>
          <p className="text-2xl font-semibold">${data.totalEarnings.toLocaleString()}</p>
          <p className="text-xs text-[rgb(var(--color-text-secondary))]">{data.orderCount} orders</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Platform Commission</p>
          <p className="text-2xl font-semibold">${(data.totalCommission / 100).toLocaleString()}</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Total Payouts</p>
          <p className="text-2xl font-semibold">${data.totalPayouts.toLocaleString()}</p>
        </div>
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <h2 className="p-4 font-semibold bg-[rgb(var(--color-surface))]">Payout History</h2>
        {data.payouts.length === 0 ? (
          <p className="p-6 text-[rgb(var(--color-text-secondary))]">No payouts yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-[rgb(var(--color-surface))] border-b">
              <tr>
                <th className="text-left p-4">Date</th>
                <th className="text-left p-4">Amount</th>
                <th className="text-left p-4">Fee</th>
                <th className="text-left p-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {data.payouts.map((p) => (
                <tr key={p.id} className="border-b border-[rgb(var(--color-border))] last:border-0">
                  <td className="p-4">{new Date(p.created_at).toLocaleDateString()}</td>
                  <td className="p-4">${((p.amount_cents ?? 0) / 100).toFixed(2)}</td>
                  <td className="p-4">${((p.fee_cents ?? 0) / 100).toFixed(2)}</td>
                  <td className="p-4 capitalize">{p.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <h2 className="p-4 font-semibold bg-[rgb(var(--color-surface))]">Commission Breakdown</h2>
        {data.commissionBreaks.length === 0 ? (
          <p className="p-6 text-[rgb(var(--color-text-secondary))]">No commission records</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-[rgb(var(--color-surface))] border-b">
              <tr>
                <th className="text-left p-4">Date</th>
                <th className="text-left p-4">Gross</th>
                <th className="text-left p-4">Commission</th>
                <th className="text-left p-4">Net</th>
              </tr>
            </thead>
            <tbody>
              {data.commissionBreaks.slice(0, 20).map((c, i) => (
                <tr key={i} className="border-b border-[rgb(var(--color-border))] last:border-0">
                  <td className="p-4">{new Date(c.created_at).toLocaleDateString()}</td>
                  <td className="p-4">${((c.gross_cents ?? 0) / 100).toFixed(2)}</td>
                  <td className="p-4">${((c.commission_cents ?? 0) / 100).toFixed(2)}</td>
                  <td className="p-4">${((c.net_cents ?? 0) / 100).toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
