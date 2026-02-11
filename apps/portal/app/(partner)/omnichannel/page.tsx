"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type OmnichannelData = {
  whatsapp: { id: string; phone: string; isActive: boolean } | null;
  api: { id: string; webhookUrl: string; isActive: boolean } | null;
};

export default function OmnichannelPage() {
  const [data, setData] = useState<OmnichannelData | null>(null);
  const [loading, setLoading] = useState(true);
  const [phone, setPhone] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => {
    fetch("/api/partners/omnichannel")
      .then((r) => r.json())
      .then((d) => {
        if (d.detail) throw new Error(d.detail);
        setData(d);
        setPhone(d.whatsapp?.phone?.replace(/^\+/, "") ?? "");
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  const handleConnectWhatsApp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim()) return;
    setSaving(true);
    try {
      const res = await fetch("/api/partners/omnichannel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel: "whatsapp", phone: phone.trim() }),
      });
      const d = await res.json();
      if (res.ok) {
        load();
      } else {
        alert(d.detail ?? "Failed to connect");
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="p-6">Loading…</p>;
  if (!data) return <p className="p-6 text-red-600">Failed to load</p>;

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold">Omnichannel Connect</h1>
      <p className="text-[rgb(var(--color-text-secondary))]">
        Connect WhatsApp to receive order updates and communicate with customers. You can also configure webhooks in{" "}
        <Link href="/integrations" className="text-[rgb(var(--color-primary))] hover:underline">
          Integrations
        </Link>
        .
      </p>

      <section className="border border-[rgb(var(--color-border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-2 flex items-center gap-2">
          <span>WhatsApp</span>
          {data.whatsapp?.isActive && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-800">Connected</span>
          )}
        </h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-4">
          Orders and negotiation updates will be sent to your WhatsApp number via Twilio.
        </p>
        {data.whatsapp ? (
          <div className="space-y-2">
            <p className="text-sm">
              Connected number: <strong>{data.whatsapp.phone}</strong>
            </p>
            <form onSubmit={handleConnectWhatsApp} className="flex gap-2 flex-wrap">
              <input
                type="tel"
                placeholder="+1 555 123 4567"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="rounded border border-[rgb(var(--color-border))] px-3 py-2 min-w-[200px]"
              />
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 rounded bg-[rgb(var(--color-primary))] text-white"
              >
                {saving ? "Updating…" : "Update Number"}
              </button>
            </form>
          </div>
        ) : (
          <form onSubmit={handleConnectWhatsApp} className="flex gap-2 flex-wrap">
            <input
              type="tel"
              placeholder="+1 555 123 4567"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="rounded border border-[rgb(var(--color-border))] px-3 py-2 min-w-[200px]"
            />
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded bg-[rgb(var(--color-primary))] text-white"
            >
              {saving ? "Connecting…" : "Connect WhatsApp"}
            </button>
          </form>
        )}
      </section>

      <section className="border border-[rgb(var(--color-border))] rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-2">API / Webhook</h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">
          Configure your webhook URL for order and negotiation callbacks.
        </p>
        <Link
          href="/integrations"
          className="inline-flex items-center gap-1 text-[rgb(var(--color-primary))] hover:underline"
        >
          Go to Integrations →
        </Link>
      </section>
    </div>
  );
}
