"use client";

import { useEffect, useState } from "react";

export function PlatformDashboard() {
  const [stats, setStats] = useState({ partners: 0, pendingApprovals: 0 });

  useEffect(() => {
    fetch("/api/platform/stats")
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch(() => {});
  }, []);

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
        <p className="text-[rgb(var(--color-text-secondary))]">Partners</p>
        <p className="text-2xl font-semibold">{stats.partners}</p>
      </div>
      <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
        <p className="text-[rgb(var(--color-text-secondary))]">Pending Approvals</p>
        <p className="text-2xl font-semibold">{stats.pendingApprovals}</p>
      </div>
    </div>
  );
}
