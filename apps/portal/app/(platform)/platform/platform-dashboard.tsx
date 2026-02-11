"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export function PlatformDashboard() {
  const [stats, setStats] = useState({
    partners: 0,
    pendingApprovals: 0,
    activeBundles: 0,
    ordersCount: 0,
    ordersToday: 0,
    revenueCents: 0,
    pendingEscalations: 0,
    vendorTasksPending: 0,
    openRfps: 0,
    period: "7d",
  });
  const [period, setPeriod] = useState("7d");

  useEffect(() => {
    fetch(`/api/platform/stats?period=${period}`)
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch(() => {});
  }, [period]);

  const revenue = (stats.revenueCents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] px-3 py-2 text-sm"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="all">All time</option>
        </select>
        <div className="flex gap-2">
          <a
            href="/api/platform/reports/export?type=partners"
            className="rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] px-3 py-2 text-sm hover:bg-[rgb(var(--color-border))]"
          >
            Export Partners
          </a>
          <a
            href="/api/platform/reports/export?type=orders"
            className="rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] px-3 py-2 text-sm hover:bg-[rgb(var(--color-border))]"
          >
            Export Orders
          </a>
          <a
            href="/api/platform/reports/export?type=escalations"
            className="rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] px-3 py-2 text-sm hover:bg-[rgb(var(--color-border))]"
          >
            Export Escalations
          </a>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Partners</p>
          <p className="text-2xl font-semibold">{stats.partners}</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Pending Approvals</p>
          <p className="text-2xl font-semibold">{stats.pendingApprovals}</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Active Bundles</p>
          <p className="text-2xl font-semibold">{stats.activeBundles}</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Orders ({period})</p>
          <p className="text-2xl font-semibold">{stats.ordersCount}</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Orders Today</p>
          <p className="text-2xl font-semibold">{stats.ordersToday}</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Revenue ({period})</p>
          <p className="text-2xl font-semibold">{revenue}</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Pending Escalations</p>
          <p className="text-2xl font-semibold">
            {stats.pendingEscalations > 0 ? (
              <Link href="/platform/escalations" className="text-amber-600 hover:underline">
                {stats.pendingEscalations}
              </Link>
            ) : (
              stats.pendingEscalations
            )}
          </p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Vendor Tasks Pending</p>
          <p className="text-2xl font-semibold">{stats.vendorTasksPending}</p>
        </div>
        <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-[rgb(var(--color-text-secondary))]">Open RFPs</p>
          <p className="text-2xl font-semibold">{stats.openRfps}</p>
        </div>
      </div>
    </div>
  );
}
