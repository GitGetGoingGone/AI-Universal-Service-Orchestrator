"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type SettingsData = {
  isAcceptingOrders: boolean;
  capacityLimit: number | null;
  aiAutoRespondEnabled: boolean;
  notificationPreferences: Record<
    string,
    { email_enabled: boolean; push_enabled: boolean; in_app_enabled: boolean }
  >;
};

export function SettingsClient() {
  const [data, setData] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [acceptingOrders, setAcceptingOrders] = useState(true);
  const [capacityLimit, setCapacityLimit] = useState<string>("");
  const [aiAutoRespondEnabled, setAiAutoRespondEnabled] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = () => {
    fetch("/api/partners/settings")
      .then((r) => r.json())
      .then((d) => {
        if (d.detail) throw new Error(d.detail);
        setData(d);
        setAcceptingOrders(d.isAcceptingOrders ?? true);
        setCapacityLimit(d.capacityLimit != null ? String(d.capacityLimit) : "");
        setAiAutoRespondEnabled(d.aiAutoRespondEnabled ?? false);
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await fetch("/api/partners/settings", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          is_accepting_orders: acceptingOrders,
          capacity_limit: capacityLimit.trim() === "" ? null : parseInt(capacityLimit, 10),
          ai_auto_respond_enabled: aiAutoRespondEnabled,
        }),
      });
      if (res.ok) load();
      else alert((await res.json()).detail ?? "Failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="mb-6">Loading…</p>;
  if (!data) return <p className="mb-6 text-red-600">Failed to load settings</p>;

  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold mb-2">Operations</h2>
      <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-4">
        Control order acceptance and capacity.
      </p>
      <form onSubmit={handleSave} className="space-y-4">
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="accepting"
            checked={acceptingOrders}
            onChange={(e) => setAcceptingOrders(e.target.checked)}
            className="rounded border-[rgb(var(--color-border))]"
          />
          <label htmlFor="accepting" className="cursor-pointer">
            Accepting orders
          </label>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="aiAutoRespond"
            checked={aiAutoRespondEnabled}
            onChange={(e) => setAiAutoRespondEnabled(e.target.checked)}
            className="rounded border-[rgb(var(--color-border))]"
          />
          <label htmlFor="aiAutoRespond" className="cursor-pointer">
            AI auto-respond for conversations (uses Knowledge Base & FAQs)
          </label>
        </div>
        <div>
          <label htmlFor="capacity" className="block text-sm mb-1">
            Capacity limit (optional)
          </label>
          <input
            id="capacity"
            type="number"
            min={0}
            placeholder="e.g. 50"
            value={capacityLimit}
            onChange={(e) => setCapacityLimit(e.target.value)}
            className="rounded border border-[rgb(var(--color-border))] px-3 py-2 w-32"
          />
          <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
            Max concurrent orders. Leave empty for unlimited.
          </p>
        </div>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 rounded bg-[rgb(var(--color-primary))] text-white"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </form>

      <div className="mt-6 pt-6 border-t border-[rgb(var(--color-border))]">
        <h2 className="text-lg font-semibold mb-2">Conversations & AI</h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">
          Manage Knowledge Base and FAQs for AI auto-respond.
        </p>
        <Link
          href="/knowledge-base"
          className="inline-flex items-center gap-1 text-[rgb(var(--color-primary))] hover:underline"
        >
          Knowledge Base →
        </Link>
        <span className="mx-2">·</span>
        <Link
          href="/faqs"
          className="inline-flex items-center gap-1 text-[rgb(var(--color-primary))] hover:underline"
        >
          FAQs →
        </Link>
      </div>

      <div className="mt-6 pt-6 border-t border-[rgb(var(--color-border))]">
        <h2 className="text-lg font-semibold mb-2">Channels & Integrations</h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">
          Connect WhatsApp and configure webhooks for order updates.
        </p>
        <Link
          href="/omnichannel"
          className="inline-flex items-center gap-1 text-[rgb(var(--color-primary))] hover:underline"
        >
          Omnichannel (WhatsApp) →
        </Link>
        <span className="mx-2">·</span>
        <Link
          href="/integrations"
          className="inline-flex items-center gap-1 text-[rgb(var(--color-primary))] hover:underline"
        >
          Integrations →
        </Link>
      </div>

      {Object.keys(data.notificationPreferences).length > 0 && (
        <div className="mt-6 pt-6 border-t border-[rgb(var(--color-border))]">
          <h2 className="text-lg font-semibold mb-2">Notification Preferences</h2>
          <p className="text-sm text-[rgb(var(--color-text-secondary))]">
            Configure per-type preferences via API. In-app notifications are enabled by default.
          </p>
        </div>
      )}
    </section>
  );
}
