"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ListTodo, MessageCircle, ShoppingCart, Zap, ArrowRight } from "lucide-react";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";

type ActionCounts = {
  pendingTasks: number;
  unassignedConversations: number;
  pendingOrders: number;
};

function ActionCard({
  href,
  title,
  description,
  count,
  icon: Icon,
}: {
  href: string;
  title: string;
  description: string;
  count: number;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Link
      href={href}
      className="group flex items-start gap-4 p-5 rounded-xl border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] hover:border-[rgb(var(--color-primary))]/50 hover:shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary))] focus:ring-offset-2"
    >
      <div className="rounded-lg bg-[rgb(var(--color-primary))]/10 p-3 text-[rgb(var(--color-primary))] shrink-0">
        <Icon className="size-6" aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <h2 className="font-semibold text-[rgb(var(--color-text))]">{title}</h2>
          {count > 0 && (
            <span className="shrink-0 rounded-full bg-[rgb(var(--color-primary))] text-[rgb(var(--color-primary-foreground))] text-sm font-medium px-2.5 py-0.5">
              {count}
            </span>
          )}
        </div>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mt-0.5">{description}</p>
        <span className="inline-flex items-center gap-1 text-sm font-medium text-[rgb(var(--color-primary))] mt-2 group-hover:gap-2 transition-all">
          View <ArrowRight className="size-4" />
        </span>
      </div>
    </Link>
  );
}

export default function ActionsPage() {
  const [counts, setCounts] = useState<ActionCounts | null>(null);
  const [loading, setLoading] = useState(true);
  const [partnerRequired, setPartnerRequired] = useState(false);

  useEffect(() => {
    fetch("/api/partners/actions")
      .then((r) => {
        if (r.status === 403) {
          setPartnerRequired(true);
          return null;
        }
        return r.json();
      })
      .then((d) => {
        if (d && !d.detail) setCounts(d);
        else setCounts({ pendingTasks: 0, unassignedConversations: 0, pendingOrders: 0 });
      })
      .catch(() => setCounts({ pendingTasks: 0, unassignedConversations: 0, pendingOrders: 0 }))
      .finally(() => setLoading(false));
  }, []);

  if (partnerRequired) return <PartnerRequiredMessage />;

  return (
    <PartnerGuard>
      <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
        <div className="flex items-center gap-2 mb-2">
          <Zap className="size-8 text-[rgb(var(--color-primary))]" aria-hidden />
          <h1 className="text-2xl font-bold text-[rgb(var(--color-text))]">Actions</h1>
        </div>
        <p className="text-[rgb(var(--color-text-secondary))] mb-8">
          Quick access to items that need your attention. Open a card to view details and take action.
        </p>

        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-24 rounded-xl border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] animate-pulse"
              />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
            <ActionCard
              href="/tasks"
              title="Pending tasks"
              description="Fulfillment tasks for orders. Complete in sequence."
              count={counts?.pendingTasks ?? 0}
              icon={ListTodo}
            />
            <ActionCard
              href="/conversations?filter=unassigned"
              title="Unassigned conversations"
              description="Customer conversations not yet assigned to a team member."
              count={counts?.unassignedConversations ?? 0}
              icon={MessageCircle}
            />
            <ActionCard
              href="/orders"
              title="Pending orders"
              description="Orders awaiting your confirmation or preparation."
              count={counts?.pendingOrders ?? 0}
              icon={ShoppingCart}
            />
          </div>
        )}

        <div className="mt-10 p-4 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
          <p className="text-sm text-[rgb(var(--color-text-secondary))]">
            <strong className="text-[rgb(var(--color-text))]">Tip:</strong> Use the{" "}
            <Link href="/conversations" className="text-[rgb(var(--color-primary))] hover:underline">
              Conversations
            </Link>{" "}
            page to reply to customers and assign threads to your team. Use{" "}
            <Link href="/tasks" className="text-[rgb(var(--color-primary))] hover:underline">
              Tasks
            </Link>{" "}
            to complete order fulfillment steps.
          </p>
        </div>
      </main>
    </PartnerGuard>
  );
}
