"use client";

import { useEffect, useState } from "react";

type AnalyticsData = {
  period: string;
  salesByDay: { date: string; revenue: number }[];
  peakHours: { hour: number; count: number }[];
  popularItems: { id: string; name: string; orderCount: number; revenue: number }[];
  totalOrders: number;
};

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [period, setPeriod] = useState("30d");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/partners/analytics?period=${period}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.detail) throw new Error(d.detail);
        setData(d);
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [period]);

  const handleExport = () => {
    if (!data) return;
    const rows = [
      ["Date", "Revenue"],
      ...data.salesByDay.map((r) => [r.date, r.revenue.toFixed(2)]),
      [],
      ["Product", "Orders", "Revenue"],
      ...data.popularItems.map((p) => [p.name, p.orderCount, p.revenue.toFixed(2)]),
      [],
      ["Peak Hour", "Orders"],
      ...data.peakHours.map((p) => [p.hour + ":00", p.count]),
    ];
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `analytics-${period}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <p className="p-6">Loading…</p>;
  if (!data) return <p className="p-6 text-red-600">Failed to load analytics</p>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <div className="flex gap-2">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="rounded border border-[rgb(var(--color-border))] px-3 py-2 bg-[rgb(var(--color-background))]"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="365d">Last year</option>
          </select>
          <button
            onClick={handleExport}
            className="px-4 py-2 rounded bg-[rgb(var(--color-primary))] text-white font-medium"
          >
            Export CSV
          </button>
        </div>
      </div>

      <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
        <p className="text-[rgb(var(--color-text-secondary))]">Total Orders</p>
        <p className="text-2xl font-semibold">{data.totalOrders}</p>
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <h2 className="p-4 font-semibold bg-[rgb(var(--color-surface))]">Peak Hours</h2>
        <div className="p-4 grid grid-cols-2 md:grid-cols-5 gap-4">
          {data.peakHours.map((p) => (
            <div key={p.hour} className="p-3 rounded border border-[rgb(var(--color-border))]">
              <p className="text-sm text-[rgb(var(--color-text-secondary))]">{p.hour}:00</p>
              <p className="font-semibold">{p.count} orders</p>
            </div>
          ))}
          {data.peakHours.length === 0 && (
            <p className="col-span-full text-[rgb(var(--color-text-secondary))]">No data</p>
          )}
        </div>
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <h2 className="p-4 font-semibold bg-[rgb(var(--color-surface))]">Popular Items</h2>
        <table className="w-full text-sm">
          <thead className="bg-[rgb(var(--color-surface))] border-b">
            <tr>
              <th className="text-left p-4">Product</th>
              <th className="text-left p-4">Orders</th>
              <th className="text-left p-4">Revenue</th>
            </tr>
          </thead>
          <tbody>
            {data.popularItems.map((p) => (
              <tr key={p.id} className="border-b border-[rgb(var(--color-border))] last:border-0">
                <td className="p-4">{p.name}</td>
                <td className="p-4">{p.orderCount}</td>
                <td className="p-4">${p.revenue.toFixed(2)}</td>
              </tr>
            ))}
            {data.popularItems.length === 0 && (
              <tr>
                <td colSpan={3} className="p-6 text-[rgb(var(--color-text-secondary))]">
                  No orders yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <h2 className="p-4 font-semibold bg-[rgb(var(--color-surface))]">Sales by Day</h2>
        <div className="p-4 max-h-64 overflow-y-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left py-2">Date</th>
                <th className="text-left py-2">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {data.salesByDay.slice(-14).reverse().map((r) => (
                <tr key={r.date} className="border-b border-[rgb(var(--color-border))]">
                  <td className="py-2">{r.date}</td>
                  <td className="py-2">${r.revenue.toFixed(2)}</td>
                </tr>
              ))}
              {data.salesByDay.length === 0 && (
                <tr>
                  <td colSpan={2} className="py-4 text-[rgb(var(--color-text-secondary))]">
                    No sales data
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
