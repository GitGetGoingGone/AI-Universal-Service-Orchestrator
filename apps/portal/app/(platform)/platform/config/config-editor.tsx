"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type LLMProvider = {
  id: string;
  name: string;
  provider_type: string;
  endpoint: string | null;
  model: string;
  display_order: number;
  has_key: boolean;
  created_at?: string;
  updated_at?: string;
};

type OpenRouterModel = {
  id: string;
  name: string;
  pricing?: { prompt?: string; completion?: string };
  supported_parameters?: string[];
};

function formatPricing(p?: { prompt?: string; completion?: string }): string {
  if (!p) return "";
  const prompt = parseFloat(p.prompt ?? "0");
  const completion = parseFloat(p.completion ?? "0");
  if (prompt === 0 && completion === 0) return "Free";
  const pPerM = (prompt * 1e6).toFixed(2);
  const cPerM = (completion * 1e6).toFixed(2);
  return `$${pPerM}/$${cPerM} per 1M tokens`;
}

function OpenRouterModelSelect({
  models,
  value,
  onChange,
}: {
  models: OpenRouterModel[];
  value: string;
  onChange: (model: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const filtered = models.filter(
    (m) =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.id.toLowerCase().includes(search.toLowerCase())
  );
  const selected = models.find((m) => m.id === value);
  return (
    <div className="relative">
      <input
        type="text"
        value={open ? search : ((selected?.name ?? value) || "Select model...")}
        onChange={(e) => {
          setSearch(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Search by name or ID..."
        className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
      />
      {open && (
        <ul className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] py-1">
          {filtered.slice(0, 50).map((m) => (
            <li
              key={m.id}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(m.id);
                setSearch("");
                setOpen(false);
              }}
              className="cursor-pointer px-3 py-2 hover:bg-[rgb(var(--color-border))]/50 text-sm"
            >
              <span className="font-medium">{m.name}</span>
              <span className="text-[rgb(var(--color-text-secondary))]"> — {m.id}</span>
              {m.pricing && (
                <span className="ml-2 text-xs text-[rgb(var(--color-text-secondary))]">
                  · {formatPricing(m.pricing)}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

type RankingPolicy = {
  strategy?: string;
  weights?: { price?: number; rating?: number; commission?: number; trust?: number };
  price_direction?: string;
};

type RankingEdgeCases = {
  missing_rating?: number;
  missing_commission?: number;
  missing_trust?: number;
  tie_breaker?: string;
};

type SponsorshipPricing = {
  product_price_per_day_cents?: number;
  max_sponsored_per_query?: number;
  sponsorship_enabled?: boolean;
};

type Config = {
  id?: string;
  commission_rate_pct?: number;
  discovery_relevance_threshold?: number;
  enable_self_registration?: boolean;
  enable_chatgpt?: boolean;
  feature_flags?: Record<string, boolean>;
  active_llm_provider_id?: string | null;
  llm_provider?: string;
  llm_model?: string;
  llm_temperature?: number;
  ranking_enabled?: boolean;
  ranking_policy?: RankingPolicy;
  ranking_edge_cases?: RankingEdgeCases;
  sponsorship_pricing?: SponsorshipPricing;
};

export function ConfigEditor() {
  const [config, setConfig] = useState<Config>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [modelSettingsExpanded, setModelSettingsExpanded] = useState(true);
  const [llmProvidersExpanded, setLlmProvidersExpanded] = useState(true);
  const [rankingExpanded, setRankingExpanded] = useState(true);
  const [sponsorshipExpanded, setSponsorshipExpanded] = useState(true);
  const [llmProviders, setLlmProviders] = useState<LLMProvider[]>([]);
  const [editingProvider, setEditingProvider] = useState<LLMProvider | null>(null);
  const [addingNew, setAddingNew] = useState(false);
  const [openRouterModels, setOpenRouterModels] = useState<OpenRouterModel[]>([]);
  const [providerForm, setProviderForm] = useState<Partial<LLMProvider> & { api_key?: string }>({
    name: "",
    provider_type: "azure",
    endpoint: "",
    model: "",
    api_key: "",
  });

  const fetchLlms = useCallback(async () => {
    try {
      const res = await fetch("/api/platform/llm-providers");
      const data = await res.json();
      if (!data.detail) setLlmProviders(Array.isArray(data) ? data : []);
    } catch {
      setLlmProviders([]);
    }
  }, []);

  useEffect(() => {
    fetch("/api/platform/config")
      .then((res) => res.json())
      .then((data) => {
        if (data.detail) return;
        const rp = data.ranking_policy ?? {};
        const rec = data.ranking_edge_cases ?? {};
        const sp = data.sponsorship_pricing ?? {};
        setConfig({
          commission_rate_pct: data.commission_rate_pct ?? 10,
          discovery_relevance_threshold: data.discovery_relevance_threshold ?? 0.7,
          enable_self_registration: data.enable_self_registration ?? true,
          enable_chatgpt: data.enable_chatgpt ?? true,
          feature_flags: data.feature_flags ?? {},
          active_llm_provider_id: data.active_llm_provider_id ?? null,
          llm_provider: data.llm_provider ?? "azure",
          llm_model: data.llm_model ?? "gpt-4o",
          llm_temperature: Number(data.llm_temperature ?? 0.1),
          ranking_enabled: data.ranking_enabled ?? true,
          ranking_policy: {
            strategy: rp.strategy ?? "weighted",
            weights: {
              price: rp.weights?.price ?? 0.3,
              rating: rp.weights?.rating ?? 0.3,
              commission: rp.weights?.commission ?? 0.2,
              trust: rp.weights?.trust ?? 0.2,
            },
            price_direction: rp.price_direction ?? "asc",
          },
          ranking_edge_cases: {
            missing_rating: rec.missing_rating ?? 0.5,
            missing_commission: rec.missing_commission ?? 0,
            missing_trust: rec.missing_trust ?? 0.5,
            tie_breaker: rec.tie_breaker ?? "created_at",
          },
          sponsorship_pricing: {
            product_price_per_day_cents: sp.product_price_per_day_cents ?? 1000,
            max_sponsored_per_query: sp.max_sponsored_per_query ?? 3,
            sponsorship_enabled: sp.sponsorship_enabled ?? true,
          },
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!loading) fetchLlms();
  }, [loading, fetchLlms]);

  useEffect(() => {
    if (providerForm.provider_type === "openrouter" && openRouterModels.length === 0) {
      fetch("/api/platform/llm-providers/openrouter-models")
        .then((r) => r.json())
        .then((d) => setOpenRouterModels(d.data ?? []))
        .catch(() => setOpenRouterModels([]));
    }
  }, [providerForm.provider_type]);

  async function setActiveProvider(id: string) {
    setConfig((c) => ({ ...c, active_llm_provider_id: id }));
    try {
      await fetch("/api/platform/config", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active_llm_provider_id: id }),
      });
    } catch {
      alert("Failed to set active provider");
    }
  }

  async function deleteProvider(id: string) {
    if (!confirm("Delete this LLM provider?")) return;
    try {
      const res = await fetch(`/api/platform/llm-providers/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail ?? "Failed");
      }
      await fetchLlms();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to delete");
    }
  }

  async function saveProvider() {
    const { name, provider_type, endpoint, model, api_key } = providerForm;
    if (!name || !model) return;
    const payload: Record<string, unknown> = {
      name,
      provider_type: provider_type ?? "azure",
      model,
    };
    if (provider_type === "azure" || provider_type === "custom") payload.endpoint = endpoint ?? "";
    if (api_key) payload.api_key = api_key;

    try {
      if (editingProvider) {
        const res = await fetch(`/api/platform/llm-providers/${editingProvider.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("Failed");
        setEditingProvider(null);
      } else {
        const res = await fetch("/api/platform/llm-providers", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error("Failed");
        setAddingNew(false);
      }
      setProviderForm({ name: "", provider_type: "azure", endpoint: "", model: "", api_key: "" });
      await fetchLlms();
    } catch {
      alert("Failed to save provider");
    }
  }

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
          active_llm_provider_id: config.active_llm_provider_id ?? null,
          llm_temperature: config.llm_temperature,
          ranking_enabled: config.ranking_enabled,
          ranking_policy: config.ranking_policy,
          ranking_edge_cases: config.ranking_edge_cases,
          sponsorship_pricing: config.sponsorship_pricing,
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
          onClick={() => setLlmProvidersExpanded((e) => !e)}
          className="flex items-center justify-between w-full text-left font-medium"
        >
          LLM Providers
          <span className="text-sm text-[rgb(var(--color-text-secondary))]">
            {llmProvidersExpanded ? "−" : "+"}
          </span>
        </button>
        {llmProvidersExpanded && (
          <div className="mt-4 space-y-4">
            {llmProviders.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between gap-4 rounded border border-[rgb(var(--color-border))] p-3"
              >
                <div className="min-w-0 flex-1">
                  <span className="font-medium">{p.name}</span>
                  <span className="ml-2 text-sm text-[rgb(var(--color-text-secondary))]">
                    {p.provider_type} · {p.model}
                  </span>
                  {config.active_llm_provider_id === p.id && (
                    <span className="ml-2 rounded bg-[rgb(var(--color-primary))]/20 px-2 py-0.5 text-xs">
                      Active
                    </span>
                  )}
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    onClick={() => setActiveProvider(p.id)}
                    className="text-sm text-[rgb(var(--color-primary))] hover:underline"
                  >
                    Use this
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setEditingProvider(p);
                      setProviderForm({
                        name: p.name,
                        provider_type: p.provider_type,
                        endpoint: p.endpoint ?? "",
                        model: p.model,
                        api_key: "",
                      });
                    }}
                    className="text-sm text-[rgb(var(--color-text-secondary))] hover:underline"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteProvider(p.id)}
                    className="text-sm text-red-600 hover:underline"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
            {(editingProvider || addingNew || llmProviders.length === 0) && (
              <div className="rounded border border-[rgb(var(--color-border))] p-4 space-y-4">
                <h4 className="font-medium">
                  {editingProvider ? "Edit provider" : "Add LLM provider"}
                </h4>
                <div>
                  <label className="block text-sm font-medium mb-1">Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Production Azure"
                    value={providerForm.name ?? ""}
                    onChange={(e) => setProviderForm((f) => ({ ...f, name: e.target.value }))}
                    className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Provider type</label>
                  <select
                    value={providerForm.provider_type ?? "azure"}
                    onChange={(e) =>
                      setProviderForm((f) => ({ ...f, provider_type: e.target.value }))
                    }
                    className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                  >
                    <option value="azure">Azure OpenAI</option>
                    <option value="gemini">Google Gemini</option>
                    <option value="openrouter">OpenRouter</option>
                    <option value="custom">Custom (OpenAI-compatible)</option>
                  </select>
                </div>
                {(providerForm.provider_type === "azure" ||
                  providerForm.provider_type === "custom") && (
                  <div>
                    <label className="block text-sm font-medium mb-1">Endpoint</label>
                    <input
                      type="url"
                      placeholder="https://..."
                      value={providerForm.endpoint ?? ""}
                      onChange={(e) =>
                        setProviderForm((f) => ({ ...f, endpoint: e.target.value }))
                      }
                      className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                    />
                  </div>
                )}
                <div>
                  <label className="block text-sm font-medium mb-1">API Key</label>
                  <input
                    type="password"
                    placeholder={editingProvider?.has_key ? "Leave blank to keep existing" : ""}
                    value={providerForm.api_key ?? ""}
                    onChange={(e) =>
                      setProviderForm((f) => ({ ...f, api_key: e.target.value }))
                    }
                    className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                  />
                </div>
                {providerForm.provider_type === "openrouter" ? (
                  <div>
                    <label className="block text-sm font-medium mb-1">Model</label>
                    <OpenRouterModelSelect
                      models={openRouterModels}
                      value={providerForm.model ?? ""}
                      onChange={(model) => setProviderForm((f) => ({ ...f, model }))}
                    />
                  </div>
                ) : (
                  <div>
                    <label className="block text-sm font-medium mb-1">Model</label>
                    <input
                      type="text"
                      placeholder="e.g. gpt-4o (from Platform Config)"
                      value={providerForm.model ?? ""}
                      onChange={(e) =>
                        setProviderForm((f) => ({ ...f, model: e.target.value }))
                      }
                      className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                    />
                  </div>
                )}
                <div className="flex gap-2">
                  <Button
                    onClick={saveProvider}
                    disabled={!providerForm.name || !providerForm.model}
                  >
                    {editingProvider ? "Update" : "Add"}
                  </Button>
                  {(editingProvider || addingNew) && (
                    <Button
                      variant="outline"
                      onClick={() => {
                        setEditingProvider(null);
                        setAddingNew(false);
                        setProviderForm({
                          name: "",
                          provider_type: "azure",
                          endpoint: "",
                          model: "",
                          api_key: "",
                        });
                      }}
                    >
                      Cancel
                    </Button>
                  )}
                </div>
              </div>
            )}
            {!editingProvider && !addingNew && llmProviders.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  setAddingNew(true);
                  setProviderForm({
                    name: "",
                    provider_type: "azure",
                    endpoint: "",
                    model: "",
                    api_key: "",
                  });
                }}
                className="text-sm text-[rgb(var(--color-primary))] hover:underline"
              >
                + Add another provider
              </button>
            )}
          </div>
        )}
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-md p-4">
        <button
          type="button"
          onClick={() => setModelSettingsExpanded((e) => !e)}
          className="flex items-center justify-between w-full text-left font-medium"
        >
          Model settings
          <span className="text-sm text-[rgb(var(--color-text-secondary))]">
            {modelSettingsExpanded ? "−" : "+"}
          </span>
        </button>
        {modelSettingsExpanded && (
          <div className="mt-4 space-y-4">
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
              <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
                Lower = more deterministic; higher = more creative. Applies to the active LLM provider.
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-md p-4">
        <button
          type="button"
          onClick={() => setRankingExpanded((e) => !e)}
          className="flex items-center justify-between w-full text-left font-medium"
        >
          Partner Ranking
          <span className="text-sm text-[rgb(var(--color-text-secondary))]">
            {rankingExpanded ? "−" : "+"}
          </span>
        </button>
        {rankingExpanded && (
          <div className="mt-4 space-y-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="ranking_enabled"
                checked={config.ranking_enabled ?? true}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, ranking_enabled: e.target.checked }))
                }
              />
              <label htmlFor="ranking_enabled">Enable partner ranking</label>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Strategy</label>
              <select
                value={config.ranking_policy?.strategy ?? "weighted"}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    ranking_policy: {
                      ...c.ranking_policy,
                      strategy: e.target.value,
                    },
                  }))
                }
                className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
              >
                <option value="weighted">Weighted (price, rating, commission, trust)</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Price weight</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={config.ranking_policy?.weights?.price ?? 0.3}
                  onChange={(e) =>
                    setConfig((c) => ({
                      ...c,
                      ranking_policy: {
                        ...c.ranking_policy,
                        weights: {
                          ...c.ranking_policy?.weights,
                          price: Number(e.target.value),
                        },
                      },
                    }))
                  }
                  className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Rating weight</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={config.ranking_policy?.weights?.rating ?? 0.3}
                  onChange={(e) =>
                    setConfig((c) => ({
                      ...c,
                      ranking_policy: {
                        ...c.ranking_policy,
                        weights: {
                          ...c.ranking_policy?.weights,
                          rating: Number(e.target.value),
                        },
                      },
                    }))
                  }
                  className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Commission weight</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={config.ranking_policy?.weights?.commission ?? 0.2}
                  onChange={(e) =>
                    setConfig((c) => ({
                      ...c,
                      ranking_policy: {
                        ...c.ranking_policy,
                        weights: {
                          ...c.ranking_policy?.weights,
                          commission: Number(e.target.value),
                        },
                      },
                    }))
                  }
                  className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Trust weight</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={config.ranking_policy?.weights?.trust ?? 0.2}
                  onChange={(e) =>
                    setConfig((c) => ({
                      ...c,
                      ranking_policy: {
                        ...c.ranking_policy,
                        weights: {
                          ...c.ranking_policy?.weights,
                          trust: Number(e.target.value),
                        },
                      },
                    }))
                  }
                  className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Price direction</label>
              <select
                value={config.ranking_policy?.price_direction ?? "asc"}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    ranking_policy: {
                      ...c.ranking_policy,
                      price_direction: e.target.value,
                    },
                  }))
                }
                className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
              >
                <option value="asc">Lower price = better rank</option>
                <option value="desc">Higher price = better rank</option>
              </select>
            </div>
            <div className="text-sm text-[rgb(var(--color-text-secondary))]">
              Edge cases: missing_rating={config.ranking_edge_cases?.missing_rating ?? 0.5},
              missing_commission={config.ranking_edge_cases?.missing_commission ?? 0},
              missing_trust={config.ranking_edge_cases?.missing_trust ?? 0.5}
            </div>
          </div>
        )}
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-md p-4">
        <button
          type="button"
          onClick={() => setSponsorshipExpanded((e) => !e)}
          className="flex items-center justify-between w-full text-left font-medium"
        >
          Sponsorship
          <span className="text-sm text-[rgb(var(--color-text-secondary))]">
            {sponsorshipExpanded ? "−" : "+"}
          </span>
        </button>
        {sponsorshipExpanded && (
          <div className="mt-4 space-y-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="sponsorship_enabled"
                checked={config.sponsorship_pricing?.sponsorship_enabled ?? true}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    sponsorship_pricing: {
                      ...c.sponsorship_pricing,
                      sponsorship_enabled: e.target.checked,
                    },
                  }))
                }
              />
              <label htmlFor="sponsorship_enabled">Enable product sponsorship</label>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Price per day (cents)</label>
              <input
                type="number"
                min="0"
                value={config.sponsorship_pricing?.product_price_per_day_cents ?? 1000}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    sponsorship_pricing: {
                      ...c.sponsorship_pricing,
                      product_price_per_day_cents: Number(e.target.value),
                    },
                  }))
                }
                className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
              />
              <span className="text-sm text-[rgb(var(--color-text-secondary))]">
                ($10/day default)
              </span>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Max sponsored per query</label>
              <input
                type="number"
                min="0"
                max="20"
                value={config.sponsorship_pricing?.max_sponsored_per_query ?? 3}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    sponsorship_pricing: {
                      ...c.sponsorship_pricing,
                      max_sponsored_per_query: Number(e.target.value),
                    },
                  }))
                }
                className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
              />
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
