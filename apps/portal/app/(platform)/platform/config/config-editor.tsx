"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

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
  const [llmExpanded, setLlmExpanded] = useState(true);
  const [rankingExpanded, setRankingExpanded] = useState(true);
  const [sponsorshipExpanded, setSponsorshipExpanded] = useState(true);

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
