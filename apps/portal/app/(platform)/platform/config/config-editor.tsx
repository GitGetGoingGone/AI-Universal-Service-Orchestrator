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

type ModelInteractionPrompt = {
  id: string;
  interaction_type: string;
  display_name: string;
  when_used: string;
  system_prompt: string | null;
  enabled: boolean;
  max_tokens: number;
  display_order: number;
};

type ExternalApiProvider = {
  id: string;
  name: string;
  api_type: string;
  base_url: string | null;
  has_key: boolean;
  enabled: boolean;
  display_order: number;
  created_at?: string;
  updated_at?: string;
};

type Config = {
  id?: string;
  commission_rate_pct?: number;
  discovery_relevance_threshold?: number;
  enable_self_registration?: boolean;
  enable_chatgpt?: boolean;
  feature_flags?: Record<string, boolean>;
  active_llm_provider_id?: string | null;
  active_image_provider_id?: string | null;
  active_external_api_ids?: Record<string, string>;
  llm_provider?: string;
  llm_model?: string;
  llm_temperature?: number;
  ranking_enabled?: boolean;
  ranking_policy?: RankingPolicy;
  ranking_edge_cases?: RankingEdgeCases;
  sponsorship_pricing?: SponsorshipPricing;
  composite_discovery_config?: {
    products_per_category?: number;
    sponsorship_enabled?: boolean;
    product_mix?: Array<{ sort: string; limit: number; pct: number }>;
  };
  enable_composite_bundle_suggestion?: boolean;
  force_model_based_intent?: boolean;
};

export function ConfigEditor() {
  const [config, setConfig] = useState<Config>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [modelSettingsExpanded, setModelSettingsExpanded] = useState(true);
  const [llmProvidersExpanded, setLlmProvidersExpanded] = useState(true);
  const [imageProvidersExpanded, setImageProvidersExpanded] = useState(true);
  const [modelInteractionsExpanded, setModelInteractionsExpanded] = useState(true);
  const [externalApisExpanded, setExternalApisExpanded] = useState(true);
  const [rankingExpanded, setRankingExpanded] = useState(true);
  const [sponsorshipExpanded, setSponsorshipExpanded] = useState(true);
  const [compositeDiscoveryExpanded, setCompositeDiscoveryExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState<"general" | "llm" | "discovery" | "integrations">("general");
  const [externalApiProviders, setExternalApiProviders] = useState<ExternalApiProvider[]>([]);
  const [addingExternalApi, setAddingExternalApi] = useState(false);
  const [externalApiForm, setExternalApiForm] = useState<Partial<ExternalApiProvider> & { api_key?: string }>({
    name: "",
    api_type: "web_search",
    base_url: "",
    api_key: "",
  });
  const [llmProviders, setLlmProviders] = useState<LLMProvider[]>([]);
  const [editingProvider, setEditingProvider] = useState<LLMProvider | null>(null);
  const [addingNew, setAddingNew] = useState(false);
  const [openRouterModels, setOpenRouterModels] = useState<OpenRouterModel[]>([]);
  const [modelInteractions, setModelInteractions] = useState<ModelInteractionPrompt[]>([]);
  const [savingModelInteractions, setSavingModelInteractions] = useState(false);
  const [testResultByInteraction, setTestResultByInteraction] = useState<
    Record<string, { response?: string; error?: string; loading?: boolean }>
  >({});
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

  const fetchModelInteractions = useCallback(async () => {
    try {
      const res = await fetch("/api/platform/model-interactions");
      const data = await res.json();
      if (!data.detail) setModelInteractions(Array.isArray(data) ? data : []);
    } catch {
      setModelInteractions([]);
    }
  }, []);

  const fetchExternalApis = useCallback(async () => {
    try {
      const res = await fetch("/api/platform/external-api-providers");
      const data = await res.json();
      if (!data.detail) setExternalApiProviders(Array.isArray(data) ? data : []);
    } catch {
      setExternalApiProviders([]);
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
          active_image_provider_id: data.active_image_provider_id ?? null,
          active_external_api_ids: data.active_external_api_ids ?? {},
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
          composite_discovery_config: data.composite_discovery_config ?? {
            products_per_category: 5,
            sponsorship_enabled: true,
            product_mix: [
              { sort: "price_desc", limit: 10, pct: 50 },
              { sort: "price_asc", limit: 10, pct: 20 },
              { sort: "rating", limit: 10, pct: 10 },
              { sort: "popularity", limit: 10, pct: 10 },
              { sort: "sponsored", limit: 10, pct: 10 },
            ],
          },
          enable_composite_bundle_suggestion: data.enable_composite_bundle_suggestion ?? true,
          force_model_based_intent: data.force_model_based_intent ?? false,
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!loading) fetchLlms();
  }, [loading, fetchLlms]);

  useEffect(() => {
    if (!loading) fetchModelInteractions();
  }, [loading, fetchModelInteractions]);

  useEffect(() => {
    if (!loading) fetchExternalApis();
  }, [loading, fetchExternalApis]);

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
    if (provider_type === "openai") payload.endpoint = null;
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
          active_image_provider_id: config.active_image_provider_id ?? null,
          llm_temperature: config.llm_temperature,
          ranking_enabled: config.ranking_enabled,
          ranking_policy: config.ranking_policy,
          ranking_edge_cases: config.ranking_edge_cases,
          sponsorship_pricing: config.sponsorship_pricing,
          composite_discovery_config: config.composite_discovery_config,
          enable_composite_bundle_suggestion: config.enable_composite_bundle_suggestion,
          force_model_based_intent: config.force_model_based_intent,
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

  const TABS = [
    { id: "general" as const, label: "General", description: "Commission, discovery threshold, and feature flags" },
    { id: "llm" as const, label: "LLM & AI", description: "Providers, image generation, model interactions" },
    { id: "discovery" as const, label: "Discovery & Ranking", description: "Partner ranking, sponsorship, composite discovery" },
    { id: "integrations" as const, label: "Integrations", description: "External APIs for events, weather, web search" },
  ];

  return (
    <div className="space-y-6 max-w-xl">
      <div className="border-b border-[rgb(var(--color-border))]">
        <div className="flex gap-1 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
                activeTab === t.id
                  ? "border-[rgb(var(--color-primary))] text-[rgb(var(--color-primary))]"
                  : "border-transparent text-[rgb(var(--color-text-secondary))] hover:text-[rgb(var(--color-text))] hover:border-[rgb(var(--color-border))]"
              }`}
              title={t.description}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "general" && (
        <div className="space-y-6">
          <p className="text-sm text-[rgb(var(--color-text-secondary))]">
            Platform-wide settings: commission rate, discovery relevance threshold, and feature toggles.
          </p>
          <div>
            <label className="block text-sm font-medium mb-1">Commission Rate (%)</label>
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mb-1">
              Default platform commission percentage applied to partner transactions.
            </p>
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
        <p className="text-xs text-[rgb(var(--color-text-secondary))] mb-1">
          Minimum similarity score for products to appear in discovery. Higher = stricter relevance.
        </p>
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
        <label htmlFor="self_reg" className="text-sm">
          Enable self-registration — Allow new partners to sign up without admin approval.
        </label>
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
        <label htmlFor="chatgpt" className="text-sm">
          Enable ChatGPT integration — Enable ChatGPT/OpenAI for chat experiences.
        </label>
      </div>
        </div>
      )}

      {activeTab === "llm" && (
        <div className="space-y-6">
          <p className="text-sm text-[rgb(var(--color-text-secondary))]">
            LLM providers, image generation, model interactions, and creativity settings.
          </p>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="force_model_intent"
          checked={config.force_model_based_intent ?? false}
          onChange={(e) =>
            setConfig((c) => ({ ...c, force_model_based_intent: e.target.checked }))
          }
        />
        <label htmlFor="force_model_intent" className="text-sm">
          Force model-based intent (ChatGPT/Gemini) — Use LLM only for intent; no heuristic fallback. Ensures probing data (date, budget, preferences) are captured. Requires LLM configured and ChatGPT/Gemini to send <code className="text-xs">messages</code>.
        </label>
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
            <p className="text-sm text-[rgb(var(--color-text-secondary))]">
              Configure LLM providers (Azure, OpenAI, OpenRouter, etc.) for chat and reasoning. Set one as active.
            </p>
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
                    <option value="openai">OpenAI (direct)</option>
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
          onClick={() => setImageProvidersExpanded((e) => !e)}
          className="flex items-center justify-between w-full text-left font-medium"
        >
          Image Generation
          <span className="text-sm text-[rgb(var(--color-text-secondary))]">
            {imageProvidersExpanded ? "−" : "+"}
          </span>
        </button>
        {imageProvidersExpanded && (
          <div className="mt-4 space-y-4">
            <p className="text-sm text-[rgb(var(--color-text-secondary))]">
              Select which provider to use for image generation (e.g. DALL-E 3). Add providers above
              with model <code className="rounded bg-[rgb(var(--color-border))]/50 px-1">dall-e-3</code>{" "}
              or similar.
            </p>
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
                  {config.active_image_provider_id === p.id && (
                    <span className="ml-2 rounded bg-[rgb(var(--color-primary))]/20 px-2 py-0.5 text-xs">
                      Active for images
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    setConfig((c) => ({ ...c, active_image_provider_id: p.id }));
                    try {
                      await fetch("/api/platform/config", {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ active_image_provider_id: p.id }),
                      });
                    } catch {
                      alert("Failed to set image provider");
                    }
                  }}
                  className="text-sm text-[rgb(var(--color-primary))] hover:underline"
                >
                  Use for images
                </button>
              </div>
            ))}
            {llmProviders.length === 0 && (
              <p className="text-sm text-[rgb(var(--color-text-secondary))]">
                Add an LLM provider above with an image model (e.g. dall-e-3) to enable image
                generation.
              </p>
            )}
          </div>
        )}
      </div>
        </div>
      )}

      {activeTab === "integrations" && (
        <div className="space-y-6">
          <p className="text-sm text-[rgb(var(--color-text-secondary))]">
            External APIs for engagement tools: events, weather, web search. Keys are encrypted.
          </p>
      <div className="border border-[rgb(var(--color-border))] rounded-md p-4">
        <button
          type="button"
          onClick={() => setExternalApisExpanded((e) => !e)}
          className="flex items-center justify-between w-full text-left font-medium"
        >
          External APIs (Events, Weather, Web Search)
          <span className="text-sm text-[rgb(var(--color-text-secondary))]">
            {externalApisExpanded ? "−" : "+"}
          </span>
        </button>
        {externalApisExpanded && (
          <div className="mt-4 space-y-4">
            <p className="text-sm text-[rgb(var(--color-text-secondary))]">
              Add external APIs for engagement tools (events, weather, web search). Keys are encrypted. Select which provider to use per type.
            </p>
            {addingExternalApi && (
              <div className="rounded border border-[rgb(var(--color-border))] p-4 space-y-3">
                <h4 className="font-medium">Add External API</h4>
                <div>
                  <label className="block text-sm mb-1">Name</label>
                  <input
                    type="text"
                    value={externalApiForm.name ?? ""}
                    onChange={(e) => setExternalApiForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder="e.g. Tavily Search"
                    className="w-full px-3 py-2 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                  />
                </div>
                <div>
                  <label className="block text-sm mb-1">API Type</label>
                  <select
                    value={externalApiForm.api_type ?? "web_search"}
                    onChange={(e) => setExternalApiForm((f) => ({ ...f, api_type: e.target.value }))}
                    className="w-full px-3 py-2 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                  >
                    <option value="web_search">Web Search</option>
                    <option value="weather">Weather</option>
                    <option value="events">Events</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm mb-1">Base URL (optional for some APIs)</label>
                  <input
                    type="text"
                    value={externalApiForm.base_url ?? ""}
                    onChange={(e) => setExternalApiForm((f) => ({ ...f, base_url: e.target.value }))}
                    placeholder="https://api.tavily.com"
                    className="w-full px-3 py-2 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                  />
                </div>
                <div>
                  <label className="block text-sm mb-1">API Key</label>
                  <input
                    type="password"
                    value={externalApiForm.api_key ?? ""}
                    onChange={(e) => setExternalApiForm((f) => ({ ...f, api_key: e.target.value }))}
                    placeholder="Your API key"
                    className="w-full px-3 py-2 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={async () => {
                      try {
                        const res = await fetch("/api/platform/external-api-providers", {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({
                            name: externalApiForm.name,
                            api_type: externalApiForm.api_type,
                            base_url: externalApiForm.base_url || undefined,
                            api_key: externalApiForm.api_key || undefined,
                          }),
                        });
                        if (!res.ok) throw new Error("Failed");
                        setAddingExternalApi(false);
                        setExternalApiForm({ name: "", api_type: "web_search", base_url: "", api_key: "" });
                        fetchExternalApis();
                      } catch {
                        alert("Failed to add external API");
                      }
                    }}
                  >
                    Save
                  </Button>
                  <Button variant="outline" onClick={() => setAddingExternalApi(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}
            {externalApiProviders.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between gap-4 rounded border border-[rgb(var(--color-border))] p-3"
              >
                <div className="min-w-0 flex-1">
                  <span className="font-medium">{p.name}</span>
                  <span className="ml-2 text-sm text-[rgb(var(--color-text-secondary))]">
                    {p.api_type}
                    {p.base_url && ` · ${p.base_url}`}
                  </span>
                  {config.active_external_api_ids?.[p.api_type] === p.id && (
                    <span className="ml-2 rounded bg-[rgb(var(--color-primary))]/20 px-2 py-0.5 text-xs">
                      Active for {p.api_type}
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    const next = { ...(config.active_external_api_ids ?? {}), [p.api_type]: p.id };
                    setConfig((c) => ({ ...c, active_external_api_ids: next }));
                    try {
                      await fetch("/api/platform/config", {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ active_external_api_ids: next }),
                      });
                    } catch {
                      alert("Failed to set external API");
                    }
                  }}
                  className="text-sm text-[rgb(var(--color-primary))] hover:underline"
                >
                  Use for {p.api_type}
                </button>
              </div>
            ))}
            {!addingExternalApi && (
              <button
                type="button"
                onClick={() => setAddingExternalApi(true)}
                className="text-sm text-[rgb(var(--color-primary))] hover:underline"
              >
                + Add external API
              </button>
            )}
          </div>
        )}
      </div>
        </div>
      )}

      {activeTab === "llm" && (
        <>
      <div className="border border-[rgb(var(--color-border))] rounded-md p-4">
        <button
          type="button"
          onClick={() => setModelInteractionsExpanded((e) => !e)}
          className="flex items-center justify-between w-full text-left font-medium"
        >
          Model Interactions
          <span className="text-sm text-[rgb(var(--color-text-secondary))]">
            {modelInteractionsExpanded ? "−" : "+"}
          </span>
        </button>
        {modelInteractionsExpanded && (
          <div className="mt-4 space-y-6">
            <p className="text-sm text-[rgb(var(--color-text-secondary))]">
              Edit system prompts per interaction type. Changes apply without redeployment. Empty prompt
              uses code default. Use <strong>Try</strong> to test each interaction with the active model—verifies connection and helps tweak prompts.
              For discover types, the test sends sample product data (Product data, Allowed CTAs) in the same format as real chat.
            </p>
            {modelInteractions.map((m) => (
              <div
                key={m.id}
                className="rounded border border-[rgb(var(--color-border))] p-4 space-y-3"
              >
                <div>
                  <span className="font-medium">{m.display_name}</span>
                  <span className="ml-2 text-xs text-[rgb(var(--color-text-secondary))]">
                    {m.interaction_type}
                  </span>
                </div>
                <p className="text-xs text-[rgb(var(--color-text-secondary))] bg-[rgb(var(--color-border))]/20 rounded px-2 py-1.5">
                  {m.when_used}
                </p>
                <div>
                  <label className="block text-sm font-medium mb-1">System prompt</label>
                  <textarea
                    rows={6}
                    value={m.system_prompt ?? ""}
                    onChange={(e) => {
                      const val = e.target.value;
                      setModelInteractions((prev) =>
                        prev.map((p) =>
                          p.interaction_type === m.interaction_type
                            ? { ...p, system_prompt: val || null }
                            : p
                        )
                      );
                    }}
                    placeholder="Leave empty to use code default"
                    className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] font-mono text-sm"
                  />
                </div>
                <div className="flex items-center gap-4 flex-wrap">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={m.enabled}
                      onChange={(e) =>
                        setModelInteractions((prev) =>
                          prev.map((p) =>
                            p.interaction_type === m.interaction_type
                              ? { ...p, enabled: e.target.checked }
                              : p
                          )
                        )
                      }
                    />
                    <span className="text-sm">Enabled</span>
                  </label>
                  <div className="flex items-center gap-2">
                    <label className="text-sm">Max tokens</label>
                    <input
                      type="number"
                      min={50}
                      max={4000}
                      value={m.max_tokens}
                      onChange={(e) => {
                        const n = parseInt(e.target.value, 10);
                        if (!Number.isNaN(n))
                          setModelInteractions((prev) =>
                            prev.map((p) =>
                              p.interaction_type === m.interaction_type
                                ? { ...p, max_tokens: Math.max(50, Math.min(4000, n)) }
                                : p
                            )
                          );
                      }}
                      className="w-20 px-2 py-1 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                    />
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={testResultByInteraction[m.interaction_type]?.loading}
                    onClick={async () => {
                      setTestResultByInteraction((prev) => ({
                        ...prev,
                        [m.interaction_type]: { loading: true },
                      }));
                      try {
                        const res = await fetch("/api/platform/model-interactions/test", {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({
                            interaction_type: m.interaction_type,
                            system_prompt_override: m.system_prompt || undefined,
                          }),
                        });
                        const data = await res.json().catch(() => ({}));
                        if (!res.ok) {
                          setTestResultByInteraction((prev) => ({
                            ...prev,
                            [m.interaction_type]: {
                              error: data.detail || "Test failed",
                            },
                          }));
                        } else {
                          setTestResultByInteraction((prev) => ({
                            ...prev,
                            [m.interaction_type]: {
                              response: data.response,
                              error: undefined,
                            },
                          }));
                        }
                      } catch {
                        setTestResultByInteraction((prev) => ({
                          ...prev,
                          [m.interaction_type]: { error: "Request failed" },
                        }));
                      }
                    }}
                  >
                    {testResultByInteraction[m.interaction_type]?.loading
                      ? "Testing..."
                      : "Try"}
                  </Button>
                </div>
                {testResultByInteraction[m.interaction_type]?.response && (
                  <div className="mt-3 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]/50 p-3">
                    <p className="text-xs font-medium text-[rgb(var(--color-text-secondary))] mb-1">
                      Model response
                    </p>
                    <pre className="text-sm whitespace-pre-wrap break-words font-sans">
                      {testResultByInteraction[m.interaction_type].response}
                    </pre>
                  </div>
                )}
                {testResultByInteraction[m.interaction_type]?.error && (
                  <div className="mt-3 rounded border border-red-500/50 bg-red-500/10 p-3">
                    <p className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">
                      Error
                    </p>
                    <p className="text-sm">
                      {testResultByInteraction[m.interaction_type].error}
                    </p>
                  </div>
                )}
              </div>
            ))}
            <Button
              onClick={async () => {
                setSavingModelInteractions(true);
                try {
                  const res = await fetch("/api/platform/model-interactions", {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      updates: modelInteractions.map((m) => ({
                        interaction_type: m.interaction_type,
                        system_prompt: m.system_prompt || null,
                        enabled: m.enabled,
                        max_tokens: m.max_tokens,
                      })),
                    }),
                  });
                  if (!res.ok) throw new Error("Failed");
                } catch {
                  alert("Failed to save model interactions");
                } finally {
                  setSavingModelInteractions(false);
                }
              }}
              disabled={savingModelInteractions || modelInteractions.length === 0}
            >
              {savingModelInteractions ? "Saving..." : "Save Model Interactions"}
            </Button>
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
            <p className="text-sm text-[rgb(var(--color-text-secondary))]">
              Control creativity (temperature) for the active LLM provider.
            </p>
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
        </>
      )}

      {activeTab === "discovery" && (
        <div className="space-y-6">
          <p className="text-sm text-[rgb(var(--color-text-secondary))]">
            Partner ranking weights, sponsorship pricing, and composite discovery (date night, bundles).
          </p>
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
            <p className="text-sm text-[rgb(var(--color-text-secondary))]">
              Configure how partners are ranked in search results. Weight price, rating, commission, and trust.
            </p>
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
            <p className="text-sm text-[rgb(var(--color-text-secondary))]">
              Configure sponsored product placement and pricing per day. Partners pay to boost visibility.
            </p>
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

      <div className="border border-[rgb(var(--color-border))] rounded-md p-4">
        <button
          type="button"
          onClick={() => setCompositeDiscoveryExpanded((e) => !e)}
          className="flex items-center justify-between w-full text-left font-medium"
        >
          Composite Discovery (Date Night, Bundles)
          <span className="text-sm text-[rgb(var(--color-text-secondary))]">
            {compositeDiscoveryExpanded ? "−" : "+"}
          </span>
        </button>
        {compositeDiscoveryExpanded && (
          <div className="mt-4 space-y-4">
            <p className="text-sm text-[rgb(var(--color-text-secondary))]">
              Products per category for composite experiences (e.g. date night: flowers, dinner, movies).
            </p>
            <div>
              <label className="block text-sm font-medium mb-1">Products per category</label>
              <input
                type="number"
                min="1"
                max="10"
                value={config.composite_discovery_config?.products_per_category ?? 5}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    composite_discovery_config: {
                      ...c.composite_discovery_config,
                      products_per_category: Math.max(1, Math.min(10, Number(e.target.value) || 5)),
                    },
                  }))
                }
                className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
              />
              <span className="text-sm text-[rgb(var(--color-text-secondary))]">
                (1–10, default 5)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="composite-sponsorship"
                checked={config.composite_discovery_config?.sponsorship_enabled ?? true}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    composite_discovery_config: {
                      ...c.composite_discovery_config,
                      sponsorship_enabled: e.target.checked,
                    },
                  }))
                }
                className="rounded border border-[rgb(var(--color-border))]"
              />
              <label htmlFor="composite-sponsorship" className="text-sm">
                Apply sponsorship boost when ranking composite results
              </label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enable-bundle-suggestion"
                checked={config.enable_composite_bundle_suggestion ?? true}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, enable_composite_bundle_suggestion: e.target.checked }))
                }
                className="rounded border border-[rgb(var(--color-border))]"
              />
              <label htmlFor="enable-bundle-suggestion" className="text-sm">
                Enable LLM bundle suggestions (2–4 options per composite experience)
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Product Mix (slices by sort, % of results)</label>
              <p className="text-xs text-[rgb(var(--color-text-secondary))] mb-2">
                Mix products from different sort criteria. Percentages should sum to 100.
              </p>
              {(config.composite_discovery_config?.product_mix ?? []).map((slice, i) => (
                <div key={i} className="flex gap-2 items-center mb-2">
                  <select
                    value={slice.sort}
                    onChange={(e) =>
                      setConfig((c) => ({
                        ...c,
                        composite_discovery_config: {
                          ...c.composite_discovery_config,
                          product_mix: (c.composite_discovery_config?.product_mix ?? []).map((s, j) =>
                            j === i ? { ...s, sort: e.target.value } : s
                          ),
                        },
                      }))
                    }
                    className="flex-1 px-2 py-1.5 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] text-sm"
                  >
                    <option value="price_desc">Price (high → low)</option>
                    <option value="price_asc">Price (low → high)</option>
                    <option value="rating">Rating</option>
                    <option value="popularity">Popularity (most sold)</option>
                    <option value="sponsored">Sponsored</option>
                    <option value="recent">Recent</option>
                  </select>
                  <span className="text-sm text-[rgb(var(--color-text-secondary))]">Top</span>
                  <input
                    type="number"
                    min="1"
                    max="50"
                    value={slice.limit}
                    onChange={(e) =>
                      setConfig((c) => ({
                        ...c,
                        composite_discovery_config: {
                          ...c.composite_discovery_config,
                          product_mix: (c.composite_discovery_config?.product_mix ?? []).map((s, j) =>
                            j === i ? { ...s, limit: Math.max(1, Math.min(50, Number(e.target.value) || 10)) } : s
                          ),
                        },
                      }))
                    }
                    className="w-14 px-2 py-1.5 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] text-sm"
                  />
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={slice.pct}
                    onChange={(e) =>
                      setConfig((c) => ({
                        ...c,
                        composite_discovery_config: {
                          ...c.composite_discovery_config,
                          product_mix: (c.composite_discovery_config?.product_mix ?? []).map((s, j) =>
                            j === i ? { ...s, pct: Math.max(0, Math.min(100, Number(e.target.value) || 0)) } : s
                          ),
                        },
                      }))
                    }
                    className="w-16 px-2 py-1.5 rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] text-sm"
                  />
                  <span className="text-sm">%</span>
                  <button
                    type="button"
                    onClick={() =>
                      setConfig((c) => ({
                        ...c,
                        composite_discovery_config: {
                          ...c.composite_discovery_config,
                          product_mix: (c.composite_discovery_config?.product_mix ?? []).filter((_, j) => j !== i),
                        },
                      }))
                    }
                    className="text-red-500 hover:underline text-sm"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() =>
                  setConfig((c) => ({
                    ...c,
                    composite_discovery_config: {
                      ...c.composite_discovery_config,
                      product_mix: [...(c.composite_discovery_config?.product_mix ?? []), { sort: "price_desc", limit: 10, pct: 20 }],
                    },
                  }))
                }
                className="text-sm text-[rgb(var(--color-primary))] hover:underline"
              >
                + Add slice
              </button>
              {(() => {
                const total = (config.composite_discovery_config?.product_mix ?? []).reduce((s, x) => s + (x.pct ?? 0), 0);
                return total !== 100 && (config.composite_discovery_config?.product_mix ?? []).length > 0 ? (
                  <p className="text-xs text-amber-600 mt-1">Percentages sum to {total}% (should be 100%)</p>
                ) : null;
              })()}
            </div>
          </div>
        )}
      </div>
        </div>
      )}

      <Button onClick={onSave} disabled={saving}>
        {saving ? "Saving..." : "Save"}
      </Button>
    </div>
  );
}
