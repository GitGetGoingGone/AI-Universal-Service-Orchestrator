"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type Config = {
  id?: string;
  commission_rate_pct?: number;
  discovery_relevance_threshold?: number;
  enable_self_registration?: boolean;
  enable_chatgpt?: boolean;
  feature_flags?: Record<string, boolean>;
  llm_provider?: string;
  llm_model?: string;
  llm_temperature?: number;
};

export function ConfigEditor() {
  const [config, setConfig] = useState<Config>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [llmExpanded, setLlmExpanded] = useState(true);

  useEffect(() => {
    fetch("/api/platform/config")
      .then((res) => res.json())
      .then((data) => {
        if (data.detail) return;
        setConfig({
          commission_rate_pct: data.commission_rate_pct ?? 10,
          discovery_relevance_threshold: data.discovery_relevance_threshold ?? 0.7,
          enable_self_registration: data.enable_self_registration ?? true,
          enable_chatgpt: data.enable_chatgpt ?? true,
          feature_flags: data.feature_flags ?? {},
          llm_provider: data.llm_provider ?? "azure",
          llm_model: data.llm_model ?? "gpt-4o",
          llm_temperature: Number(data.llm_temperature ?? 0.1),
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function onSave() {
    setSaving(true);
    try {
      const res = await fetch("/api/platform/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          commission_rate_pct: config.commission_rate_pct,
          discovery_relevance_threshold: config.discovery_relevance_threshold,
          enable_self_registration: config.enable_self_registration,
          enable_chatgpt: config.enable_chatgpt,
          feature_flags: config.feature_flags,
          llm_provider: config.llm_provider,
          llm_model: config.llm_model,
          llm_temperature: config.llm_temperature,
        }),
      });
      if (!res.ok) throw new Error("Failed");
    } catch {
      alert("Failed to save");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <label className="block text-sm font-medium mb-1">Commission Rate (%)</label>
        <input
          type="number"
          step="0.01"
          min="0"
          max="100"
          value={config.commission_rate_pct ?? 10}
          onChange={(e) =>
            setConfig((c) => ({ ...c, commission_rate_pct: Number(e.target.value) }))
          }
          className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">
          Discovery Relevance Threshold (0–1)
        </label>
        <input
          type="number"
          step="0.01"
          min="0"
          max="1"
          value={config.discovery_relevance_threshold ?? 0.7}
          onChange={(e) =>
            setConfig((c) => ({
              ...c,
              discovery_relevance_threshold: Number(e.target.value),
            }))
          }
          className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="self_reg"
          checked={config.enable_self_registration ?? true}
          onChange={(e) =>
            setConfig((c) => ({ ...c, enable_self_registration: e.target.checked }))
          }
        />
        <label htmlFor="self_reg">Enable self-registration</label>
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="chatgpt"
          checked={config.enable_chatgpt ?? true}
          onChange={(e) =>
            setConfig((c) => ({ ...c, enable_chatgpt: e.target.checked }))
          }
        />
        <label htmlFor="chatgpt">Enable ChatGPT integration</label>
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-md p-4">
        <button
          type="button"
          onClick={() => setLlmExpanded((e) => !e)}
          className="flex items-center justify-between w-full text-left font-medium"
        >
          LLM Settings
          <span className="text-sm text-[rgb(var(--color-text-secondary))]">
            {llmExpanded ? "−" : "+"}
          </span>
        </button>
        {llmExpanded && (
          <div className="mt-4 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Provider</label>
              <select
                value={config.llm_provider ?? "azure"}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, llm_provider: e.target.value }))
                }
                className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
              >
                <option value="azure">Azure OpenAI</option>
                <option value="gemini">Google Gemini</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Model</label>
              <input
                type="text"
                placeholder="gpt-4o, gemini-1.5-flash, etc."
                value={config.llm_model ?? "gpt-4o"}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, llm_model: e.target.value }))
                }
                className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Creativity (0–1)
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={config.llm_temperature ?? 0.1}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    llm_temperature: Number(e.target.value),
                  }))
                }
                className="w-full"
              />
              <span className="text-sm text-[rgb(var(--color-text-secondary))]">
                {(config.llm_temperature ?? 0.1).toFixed(2)}
              </span>
            </div>
          </div>
        )}
      </div>

      <Button onClick={onSave} disabled={saving}>
        {saving ? "Saving..." : "Save"}
      </Button>
    </div>
  );
}
