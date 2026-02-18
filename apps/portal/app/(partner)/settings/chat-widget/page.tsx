"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type ChatConfig = {
  partner_id: string;
  primary_color: string;
  secondary_color: string;
  font_family: string;
  font_size_px?: number;
  logo_url: string | null;
  welcome_message: string;
  embed_enabled: boolean;
  embed_domains: string[];
  e2e_add_to_bundle: boolean;
  e2e_checkout: boolean;
  e2e_payment: boolean;
  chat_typing_enabled?: boolean;
  chat_typing_speed_ms?: number;
};

export default function ChatWidgetSettingsPage() {
  const [config, setConfig] = useState<ChatConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [embedDomainsStr, setEmbedDomainsStr] = useState("");

  useEffect(() => {
    fetch("/api/partners/chat-config")
      .then((r) => r.json())
      .then((d) => {
        if (d.detail) throw new Error(d.detail);
        setConfig(d);
        setEmbedDomainsStr(Array.isArray(d.embed_domains) ? d.embed_domains.join("\n") : "");
      })
      .catch(() => setConfig(null))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    setSaving(true);
    try {
      const domains = embedDomainsStr
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      const res = await fetch("/api/partners/chat-config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...config,
          embed_domains: domains,
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setConfig(updated);
        setEmbedDomainsStr(Array.isArray(updated.embed_domains) ? updated.embed_domains.join("\n") : "");
      } else {
        const err = await res.json();
        alert(err.detail ?? "Failed to save");
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="mb-6">Loading…</p>;
  if (!config) return <p className="mb-6 text-red-600">Failed to load chat widget settings</p>;

  const embedBase =
    process.env.NEXT_PUBLIC_CHAT_APP_URL || "https://uso-unified-chat.vercel.app";
  const embedSnippet = `<script src="${embedBase}/embed.js" data-partner-id="${config.partner_id}"></script>`;

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <div className="mb-6">
        <Link href="/settings" className="text-sm text-[rgb(var(--color-primary))] hover:underline">
          ← Settings
        </Link>
      </div>
      <h1 className="text-2xl font-bold mb-6">Chat Widget</h1>
      <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-6">
        Configure the look and feel of the chat widget for your website. Embed the widget on your site to let customers discover and purchase your products.
      </p>

      <form onSubmit={handleSave} className="space-y-6">
        <section>
          <h2 className="text-lg font-semibold mb-3">Theme</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm mb-1">Primary color</label>
              <input
                type="color"
                value={config.primary_color}
                onChange={(e) => setConfig({ ...config, primary_color: e.target.value })}
                className="h-10 w-full rounded border border-[rgb(var(--color-border))]"
              />
              <input
                type="text"
                value={config.primary_color}
                onChange={(e) => setConfig({ ...config, primary_color: e.target.value })}
                className="mt-1 w-24 rounded border border-[rgb(var(--color-border))] px-2 py-1 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Secondary color</label>
              <input
                type="color"
                value={config.secondary_color}
                onChange={(e) => setConfig({ ...config, secondary_color: e.target.value })}
                className="h-10 w-full rounded border border-[rgb(var(--color-border))]"
              />
              <input
                type="text"
                value={config.secondary_color}
                onChange={(e) => setConfig({ ...config, secondary_color: e.target.value })}
                className="mt-1 w-24 rounded border border-[rgb(var(--color-border))] px-2 py-1 text-sm"
              />
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm mb-1">Font family</label>
            <input
              type="text"
              value={config.font_family}
              onChange={(e) => setConfig({ ...config, font_family: e.target.value })}
              placeholder="Inter, sans-serif"
              className="w-full max-w-md rounded border border-[rgb(var(--color-border))] px-3 py-2"
            />
          </div>
          <div className="mt-4">
            <label className="block text-sm mb-1">Font size (px)</label>
            <input
              type="number"
              min={12}
              max={24}
              value={config.font_size_px ?? 14}
              onChange={(e) =>
                setConfig({
                  ...config,
                  font_size_px: Math.max(12, Math.min(24, parseInt(e.target.value, 10) || 14)),
                })
              }
              className="w-24 rounded border border-[rgb(var(--color-border))] px-3 py-2"
            />
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
              Base font size for chat messages (12–24px).
            </p>
          </div>
          <div className="mt-4">
            <label className="block text-sm mb-1">Logo URL (optional)</label>
            <input
              type="url"
              value={config.logo_url ?? ""}
              onChange={(e) => setConfig({ ...config, logo_url: e.target.value || null })}
              placeholder="https://..."
              className="w-full max-w-md rounded border border-[rgb(var(--color-border))] px-3 py-2"
            />
          </div>
          <div className="mt-4">
            <label className="block text-sm mb-1">Welcome message</label>
            <input
              type="text"
              value={config.welcome_message}
              onChange={(e) => setConfig({ ...config, welcome_message: e.target.value })}
              placeholder="How can I help you today?"
              className="w-full max-w-md rounded border border-[rgb(var(--color-border))] px-3 py-2"
            />
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold mb-3">Embed</h2>
          <div className="flex items-center gap-3 mb-4">
            <input
              type="checkbox"
              id="embed_enabled"
              checked={config.embed_enabled}
              onChange={(e) => setConfig({ ...config, embed_enabled: e.target.checked })}
              className="rounded border-[rgb(var(--color-border))]"
            />
            <label htmlFor="embed_enabled" className="cursor-pointer">
              Enable embed on partner websites
            </label>
          </div>
          <div className="mb-4">
            <label className="block text-sm mb-1">Allowed domains (one per line)</label>
            <textarea
              value={embedDomainsStr}
              onChange={(e) => setEmbedDomainsStr(e.target.value)}
              placeholder="example.com&#10;www.example.com"
              rows={3}
              className="w-full max-w-md rounded border border-[rgb(var(--color-border))] px-3 py-2 font-mono text-sm"
            />
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
              Leave empty to allow all origins (not recommended for production).
            </p>
          </div>
          <div>
            <label className="block text-sm mb-1">Embed code</label>
            <pre className="bg-[rgb(var(--color-border))] rounded p-4 text-sm overflow-x-auto">
              {embedSnippet}
            </pre>
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
              Add this script to your website to show the chat widget.
            </p>
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold mb-3">Message Display</h2>
          <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-4">
            Control how assistant messages appear in the chat.
          </p>
          <div className="space-y-4 mb-6">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="chat_typing_enabled"
                checked={config.chat_typing_enabled !== false}
                onChange={(e) =>
                  setConfig({ ...config, chat_typing_enabled: e.target.checked })
                }
                className="rounded border-[rgb(var(--color-border))]"
              />
              <label htmlFor="chat_typing_enabled" className="cursor-pointer">
                Enable typewriter effect for assistant messages
              </label>
            </div>
            {(config.chat_typing_enabled !== false) && (
              <div>
                <label className="block text-sm mb-1">Typing speed (ms per character)</label>
                <input
                  type="number"
                  min={10}
                  max={200}
                  value={config.chat_typing_speed_ms ?? 30}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      chat_typing_speed_ms: Math.max(
                        10,
                        Math.min(200, parseInt(e.target.value, 10) || 30)
                      ),
                    })
                  }
                  className="w-24 rounded border border-[rgb(var(--color-border))] px-3 py-2"
                />
                <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
                  Lower = faster. 10–200ms.
                </p>
              </div>
            )}
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold mb-3">E2E Features</h2>
          <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-4">
            Control which actions customers can take in the chat. Admin can override these settings.
          </p>
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="e2e_bundle"
                checked={config.e2e_add_to_bundle}
                onChange={(e) => setConfig({ ...config, e2e_add_to_bundle: e.target.checked })}
                className="rounded border-[rgb(var(--color-border))]"
              />
              <label htmlFor="e2e_bundle">Add to Bundle</label>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="e2e_checkout"
                checked={config.e2e_checkout}
                onChange={(e) => setConfig({ ...config, e2e_checkout: e.target.checked })}
                className="rounded border-[rgb(var(--color-border))]"
              />
              <label htmlFor="e2e_checkout">Checkout</label>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="e2e_payment"
                checked={config.e2e_payment}
                onChange={(e) => setConfig({ ...config, e2e_payment: e.target.checked })}
                className="rounded border-[rgb(var(--color-border))]"
              />
              <label htmlFor="e2e_payment">Payment</label>
            </div>
          </div>
        </section>

        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 rounded bg-[rgb(var(--color-primary))] text-white"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </form>
    </main>
  );
}
