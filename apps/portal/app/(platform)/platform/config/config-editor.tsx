"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type PlatformConfig = {
  id?: string;
  commission_rate_pct?: number;
  discovery_relevance_threshold?: number;
  enable_self_registration?: boolean;
  enable_chatgpt?: boolean;
  llm_provider?: string;
  llm_model?: string;
  llm_temperature?: number;
  active_llm_provider_id?: string | null;
  ranking_enabled?: boolean;
  ranking_policy?: string;
  enable_composite_bundle_suggestion?: boolean;
  force_model_based_intent?: boolean;
  [key: string]: unknown;
};

type LlmProvider = {
  id: string;
  name: string;
  provider_type: string;
  model: string;
  has_key: boolean;
};

export function ConfigEditor() {
  const [config, setConfig] = useState<PlatformConfig | null>(null);
  const [llmProviders, setLlmProviders] = useState<LlmProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = () => {
    Promise.all([
      fetch("/api/platform/config").then((r) => r.json()),
      fetch("/api/platform/llm-providers").then((r) => r.json()),
    ])
      .then(([configData, providersData]) => {
        if (configData.detail) throw new Error(configData.detail);
        if (Array.isArray(providersData)) {
          setLlmProviders(providersData);
        } else {
          setLlmProviders([]);
        }
        setConfig(configData ?? {});
      })
      .catch(() => setConfig({}))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    setSaving(true);
    try {
      const res = await fetch("/api/platform/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        const updated = await res.json();
        setConfig(updated);
      } else {
        const err = await res.json();
        alert(err.detail ?? "Failed to save");
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="mb-6">Loading…</p>;
  if (!config) return <p className="mb-6 text-red-600">Failed to load config</p>;

  return (
    <form onSubmit={handleSave} className="space-y-8">
      <section>
        <h2 className="text-lg font-semibold mb-3">General</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm mb-1">Commission rate (%)</label>
            <input
              type="number"
              min={0}
              max={100}
              step={0.1}
              value={config.commission_rate_pct ?? ""}
              onChange={(e) =>
                setConfig({
                  ...config,
                  commission_rate_pct: e.target.value === "" ? undefined : Number(e.target.value),
                })
              }
              className="w-32 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Discovery relevance threshold</label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={config.discovery_relevance_threshold ?? ""}
              onChange={(e) =>
                setConfig({
                  ...config,
                  discovery_relevance_threshold:
                    e.target.value === "" ? undefined : Number(e.target.value),
                })
              }
              className="w-32 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-3 py-2 text-sm"
            />
          </div>
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_self_registration"
              checked={config.enable_self_registration ?? false}
              onChange={(e) =>
                setConfig({ ...config, enable_self_registration: e.target.checked })
              }
              className="rounded border-[rgb(var(--color-border))]"
            />
            <label htmlFor="enable_self_registration" className="cursor-pointer">
              Enable self-registration
            </label>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_chatgpt"
              checked={config.enable_chatgpt ?? false}
              onChange={(e) => setConfig({ ...config, enable_chatgpt: e.target.checked })}
              className="rounded border-[rgb(var(--color-border))]"
            />
            <label htmlFor="enable_chatgpt" className="cursor-pointer">
              Enable ChatGPT integration
            </label>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">LLM Settings</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm mb-1">Active LLM provider</label>
            <select
              value={config.active_llm_provider_id ?? ""}
              onChange={(e) =>
                setConfig({
                  ...config,
                  active_llm_provider_id: e.target.value || null,
                })
              }
              className="w-full max-w-md rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-3 py-2 text-sm"
            >
              <option value="">— Select provider —</option>
              {llmProviders.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.provider_type} / {p.model})
                  {!p.has_key ? " — no API key" : ""}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1">LLM model (fallback)</label>
            <input
              type="text"
              value={config.llm_model ?? ""}
              onChange={(e) => setConfig({ ...config, llm_model: e.target.value })}
              placeholder="e.g. gpt-4o"
              className="w-full max-w-md rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm mb-1">Temperature (0–1)</label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.1}
              value={config.llm_temperature ?? ""}
              onChange={(e) =>
                setConfig({
                  ...config,
                  llm_temperature:
                    e.target.value === "" ? undefined : Number(e.target.value),
                })
              }
              className="w-32 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-3 py-2 text-sm"
            />
          </div>
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="enable_composite_bundle_suggestion"
              checked={config.enable_composite_bundle_suggestion ?? false}
              onChange={(e) =>
                setConfig({
                  ...config,
                  enable_composite_bundle_suggestion: e.target.checked,
                })
              }
              className="rounded border-[rgb(var(--color-border))]"
            />
            <label htmlFor="enable_composite_bundle_suggestion" className="cursor-pointer">
              Enable composite bundle suggestions
            </label>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="force_model_based_intent"
              checked={config.force_model_based_intent ?? false}
              onChange={(e) =>
                setConfig({ ...config, force_model_based_intent: e.target.checked })
              }
              className="rounded border-[rgb(var(--color-border))]"
            />
            <label htmlFor="force_model_based_intent" className="cursor-pointer">
              Force model-based intent (skip keyword matching)
            </label>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Ranking</h2>
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="ranking_enabled"
              checked={config.ranking_enabled ?? false}
              onChange={(e) =>
                setConfig({ ...config, ranking_enabled: e.target.checked })
              }
              className="rounded border-[rgb(var(--color-border))]"
            />
            <label htmlFor="ranking_enabled" className="cursor-pointer">
              Enable partner ranking
            </label>
          </div>
          <div>
            <label className="block text-sm mb-1">Ranking policy (JSON)</label>
            <textarea
              value={
                typeof config.ranking_policy === "string"
                  ? config.ranking_policy
                  : JSON.stringify(config.ranking_policy ?? {}, null, 2)
              }
              onChange={(e) => setConfig({ ...config, ranking_policy: e.target.value })}
              rows={6}
              className="w-full max-w-2xl rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-3 py-2 font-mono text-sm"
            />
          </div>
        </div>
      </section>

      <div>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </form>
  );
}
