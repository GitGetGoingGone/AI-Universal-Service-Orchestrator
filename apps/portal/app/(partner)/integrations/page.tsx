"use client";

import { useEffect, useState } from "react";

type ApiKey = {
  id: string;
  key_prefix: string;
  name: string | null;
  last_used_at: string | null;
  is_active: boolean;
  created_at: string;
};

type IntegrationsData = {
  webhookUrl: string;
  apiKeys: ApiKey[];
  availabilityIntegrations: { id: string; integration_type: string; provider: string | null; is_active: boolean }[];
};

export default function IntegrationsPage() {
  const [data, setData] = useState<IntegrationsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [savingWebhook, setSavingWebhook] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [creatingKey, setCreatingKey] = useState(false);
  const [newKeyRaw, setNewKeyRaw] = useState<string | null>(null);

  const load = () => {
    fetch("/api/partners/integrations")
      .then((r) => r.json())
      .then((d) => {
        if (d.detail) throw new Error(d.detail);
        setData(d);
        setWebhookUrl(d.webhookUrl ?? "");
      })
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), []);

  const handleSaveWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingWebhook(true);
    try {
      const res = await fetch("/api/partners/integrations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "webhook", url: webhookUrl }),
      });
      if (res.ok) load();
      else alert((await res.json()).detail ?? "Failed");
    } finally {
      setSavingWebhook(false);
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingKey(true);
    setNewKeyRaw(null);
    try {
      const res = await fetch("/api/partners/integrations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "api_key", name: newKeyName || "API Key" }),
      });
      const d = await res.json();
      if (res.ok) {
        setNewKeyRaw(d.rawKey ?? null);
        setNewKeyName("");
        load();
      } else {
        alert(d.detail ?? "Failed");
      }
    } finally {
      setCreatingKey(false);
    }
  };

  const handleRevokeKey = async (id: string) => {
    if (!confirm("Revoke this API key?")) return;
    const res = await fetch(`/api/partners/integrations/keys/${id}`, { method: "DELETE" });
    if (res.ok) load();
  };

  if (loading) return <p className="p-6">Loading…</p>;
  if (!data) return <p className="p-6 text-red-600">Failed to load integrations</p>;

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold">Integrations</h1>

      <section>
        <h2 className="text-lg font-semibold mb-3">Webhook URL</h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">
          Orders and updates will be pushed to this URL. Must be HTTPS.
        </p>
        <form onSubmit={handleSaveWebhook} className="flex gap-2 flex-wrap">
          <input
            type="url"
            placeholder="https://..."
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            className="flex-1 min-w-[280px] rounded border border-[rgb(var(--color-border))] px-3 py-2"
          />
          <button
            type="submit"
            disabled={savingWebhook}
            className="px-4 py-2 rounded bg-[rgb(var(--color-primary))] text-white"
          >
            {savingWebhook ? "Saving…" : "Save"}
          </button>
        </form>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">API Keys</h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-4">
          Use API keys for programmatic access (orders, products, etc.).
        </p>
        <form onSubmit={handleCreateKey} className="flex gap-2 mb-4">
          <input
            type="text"
            placeholder="Key name (optional)"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            className="rounded border border-[rgb(var(--color-border))] px-3 py-2 min-w-[160px]"
          />
          <button
            type="submit"
            disabled={creatingKey}
            className="px-4 py-2 rounded bg-[rgb(var(--color-primary))] text-white"
          >
            {creatingKey ? "Creating…" : "Create Key"}
          </button>
        </form>
        {newKeyRaw && (
          <div className="p-4 rounded bg-amber-50 border border-amber-200 mb-4">
            <p className="text-sm font-medium mb-1">Copy this key now. It won&apos;t be shown again.</p>
            <code className="text-sm break-all">{newKeyRaw}</code>
          </div>
        )}
        <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[rgb(var(--color-surface))] border-b">
              <tr>
                <th className="text-left p-4">Name</th>
                <th className="text-left p-4">Prefix</th>
                <th className="text-left p-4">Last used</th>
                <th className="text-left p-4">Status</th>
                <th className="text-left p-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.apiKeys.map((k) => (
                <tr key={k.id} className="border-b border-[rgb(var(--color-border))] last:border-0">
                  <td className="p-4">{k.name || "—"}</td>
                  <td className="p-4 font-mono">{k.key_prefix}…</td>
                  <td className="p-4">{k.last_used_at ? new Date(k.last_used_at).toLocaleString() : "Never"}</td>
                  <td className="p-4">{k.is_active ? "Active" : "Revoked"}</td>
                  <td className="p-4">
                    {k.is_active && (
                      <button
                        onClick={() => handleRevokeKey(k.id)}
                        className="text-red-600 text-sm hover:underline"
                      >
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.apiKeys.length === 0 && (
            <p className="p-6 text-[rgb(var(--color-text-secondary))]">No API keys</p>
          )}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Availability Integrations</h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">
          Connect external calendars or booking systems to sync availability.
        </p>
        {data.availabilityIntegrations.length === 0 ? (
          <p className="p-4 rounded-lg bg-[rgb(var(--color-surface))] text-[rgb(var(--color-text-secondary))]">
            No availability integrations yet. Configure via API or contact support.
          </p>
        ) : (
          <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-[rgb(var(--color-surface))] border-b">
                <tr>
                  <th className="text-left p-4">Type</th>
                  <th className="text-left p-4">Provider</th>
                  <th className="text-left p-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.availabilityIntegrations.map((a) => (
                  <tr key={a.id} className="border-b border-[rgb(var(--color-border))] last:border-0">
                    <td className="p-4">{a.integration_type}</td>
                    <td className="p-4">{a.provider || "—"}</td>
                    <td className="p-4">{a.is_active ? "Active" : "Inactive"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
