"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  LayoutDashboard,
  Users,
  ShoppingCart,
  DollarSign,
  MessageSquare,
  TrendingUp,
  AlertCircle,
  FileText,
  Package,
  Download,
  BarChart3,
} from "lucide-react";

type DashboardStats = {
  partners: number;
  pendingApprovals: number;
  activeBundles: number;
  ordersCount: number;
  ordersToday: number;
  revenueCents: number;
  pendingEscalations: number;
  vendorTasksPending: number;
  openRfps: number;
  conversationsTotal: number;
  conversationsActive: number;
  experienceSessions: number;
  conversionRate: number;
  period: string;
};

const PERIOD_LABELS: Record<string, string> = {
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  all: "All time",
};

function StatCard({
  title,
  value,
  sub,
  href,
  icon: Icon,
  variant = "default",
}: {
  title: string;
  value: string | number;
  sub?: string;
  href?: string;
  icon: React.ComponentType<{ className?: string }>;
  variant?: "default" | "highlight" | "muted";
}) {
  const base =
    "block p-5 rounded-xl border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] transition-colors text-left";
  const hover = href ? "hover:border-[rgb(var(--color-primary))]/50 hover:shadow-sm" : "";
  const variantStyles =
    variant === "highlight"
      ? "border-[rgb(var(--color-primary))]/30 bg-[rgb(var(--color-primary))]/5"
      : variant === "muted"
        ? "bg-[rgb(var(--color-background))]"
        : "";

  const className = `${base} ${hover} ${variantStyles}`;
  const content = (
    <>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-[rgb(var(--color-text-secondary))]">{title}</p>
          <p className="text-2xl font-semibold text-[rgb(var(--color-text))] mt-1 tabular-nums">
            {value}
          </p>
          {sub != null && (
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">{sub}</p>
          )}
        </div>
        <div className="rounded-lg bg-[rgb(var(--color-primary))]/10 p-2 text-[rgb(var(--color-primary))] shrink-0">
          <Icon className="size-5" aria-hidden />
        </div>
      </div>
    </>
  );

  if (href) {
    return (
      <Link href={href} className={className}>
        {content}
      </Link>
    );
  }
  return <div className={className}>{content}</div>;
}

export function PlatformDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [period, setPeriod] = useState("7d");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/platform/stats?period=${period}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.detail) throw new Error(data.detail);
        setStats(data);
      })
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, [period]);

  const revenue =
    stats != null
      ? (stats.revenueCents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" })
      : "—";

  if (loading && !stats) {
    return (
      <div className="space-y-8">
        <div className="flex justify-between items-center flex-wrap gap-4">
          <div className="h-10 w-48 rounded-lg bg-[rgb(var(--color-border))]/30 animate-pulse" />
          <div className="h-10 w-64 rounded-lg bg-[rgb(var(--color-border))]/30 animate-pulse" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-[rgb(var(--color-border))]/30 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const s = stats ?? {
    partners: 0,
    pendingApprovals: 0,
    activeBundles: 0,
    ordersCount: 0,
    ordersToday: 0,
    revenueCents: 0,
    pendingEscalations: 0,
    vendorTasksPending: 0,
    openRfps: 0,
    conversationsTotal: 0,
    conversationsActive: 0,
    experienceSessions: 0,
    conversionRate: 0,
    period: "7d",
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="size-6 text-[rgb(var(--color-primary))]" aria-hidden />
          <h2 className="text-lg font-semibold text-[rgb(var(--color-text))]">Metrics</h2>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            aria-label="Time period"
            className="rounded-lg border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] px-3 py-2 text-sm text-[rgb(var(--color-text))] focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary))]"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="all">All time</option>
          </select>
          <div className="flex gap-2">
            <a
              href="/api/platform/reports/export?type=partners"
              className="inline-flex items-center gap-2 rounded-lg border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] px-3 py-2 text-sm hover:bg-[rgb(var(--color-border))]/30 transition-colors"
            >
              <Download className="size-4" aria-hidden />
              Partners
            </a>
            <a
              href="/api/platform/reports/export?type=orders"
              className="inline-flex items-center gap-2 rounded-lg border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] px-3 py-2 text-sm hover:bg-[rgb(var(--color-border))]/30 transition-colors"
            >
              <Download className="size-4" aria-hidden />
              Orders
            </a>
            <a
              href="/api/platform/reports/export?type=escalations"
              className="inline-flex items-center gap-2 rounded-lg border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] px-3 py-2 text-sm hover:bg-[rgb(var(--color-border))]/30 transition-colors"
            >
              <Download className="size-4" aria-hidden />
              Escalations
            </a>
          </div>
        </div>
      </div>

      <section aria-labelledby="overview-heading">
        <h3 id="overview-heading" className="text-sm font-medium uppercase tracking-wider text-[rgb(var(--color-text-secondary))] mb-4">
          Overview
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Partners"
            value={s.partners}
            sub={s.pendingApprovals > 0 ? `${s.pendingApprovals} pending approval` : undefined}
            href="/platform/partners"
            icon={Users}
          />
          <StatCard
            title={`Orders (${PERIOD_LABELS[s.period] ?? s.period})`}
            value={s.ordersCount}
            sub={`${s.ordersToday} today`}
            href="/platform/orders"
            icon={ShoppingCart}
          />
          <StatCard
            title={`Revenue (${PERIOD_LABELS[s.period] ?? s.period})`}
            value={revenue}
            href="/platform/orders"
            icon={DollarSign}
          />
          <StatCard
            title="Conversion rate"
            value={s.conversionRate > 0 ? `${s.conversionRate}%` : "—"}
            sub={s.experienceSessions > 0 ? `Orders / ${s.experienceSessions} sessions` : "Sessions → orders"}
            icon={TrendingUp}
            variant={s.conversionRate > 0 ? "highlight" : "muted"}
          />
        </div>
      </section>

      <section aria-labelledby="conversations-heading">
        <h3 id="conversations-heading" className="text-sm font-medium uppercase tracking-wider text-[rgb(var(--color-text-secondary))] mb-4">
          Conversations & sessions
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <StatCard
            title="Conversations (total)"
            value={s.conversationsTotal}
            sub="Partner conversations"
            icon={MessageSquare}
          />
          <StatCard
            title="Conversations (active)"
            value={s.conversationsActive}
            sub="Currently active"
            icon={MessageSquare}
            variant="highlight"
          />
          <StatCard
            title={`Experience sessions (${PERIOD_LABELS[s.period] ?? s.period})`}
            value={s.experienceSessions}
            sub="Bundle/thread sessions"
            href="/platform/experience-sessions"
            icon={LayoutDashboard}
          />
        </div>
      </section>

      <section aria-labelledby="operations-heading">
        <h3 id="operations-heading" className="text-sm font-medium uppercase tracking-wider text-[rgb(var(--color-text-secondary))] mb-4">
          Operations & sentiment
        </h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Pending escalations"
            value={s.pendingEscalations}
            sub="Support escalations"
            href={s.pendingEscalations > 0 ? "/platform/escalations" : undefined}
            icon={AlertCircle}
            variant={s.pendingEscalations > 0 ? "highlight" : "default"}
          />
          <StatCard
            title="Vendor tasks pending"
            value={s.vendorTasksPending}
            sub="Task queue"
            icon={Package}
          />
          <StatCard
            title="Open RFPs"
            value={s.openRfps}
            sub="Hub RFPs"
            href="/platform/rfps"
            icon={FileText}
          />
          <StatCard
            title="Active bundles"
            value={s.activeBundles}
            sub="Draft or in progress"
            icon={Package}
            variant="muted"
          />
        </div>
        <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-2">
          Sentiment metrics (e.g. from escalations or conversation analysis) can be added via integrations or future modules.
        </p>
      </section>
    </div>
  );
}
