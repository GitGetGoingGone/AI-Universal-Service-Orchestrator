"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

type Mode = "manifest" | "manual";

export function AddUCPPartnerForm() {
  const [mode, setMode] = useState<Mode>("manual");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ registry_id?: string; base_url?: string } | null>(null);

  const [baseUrl, setBaseUrl] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [manifestJson, setManifestJson] = useState("");
  const [pricePremiumPercent, setPricePremiumPercent] = useState(0);
  const [availableToCustomize, setAvailableToCustomize] = useState(false);
  const [accessToken, setAccessToken] = useState("");

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    const payload: Record<string, string | number | boolean> = {};
    if (mode === "manifest") {
      const raw = manifestJson.trim();
      if (!raw) {
        setError("Paste the UCP manifest JSON.");
        setLoading(false);
        return;
      }
      payload.manifest_json = raw;
      if (displayName.trim()) payload.display_name = displayName.trim();
      if (baseUrl.trim()) payload.base_url = baseUrl.trim();
    } else {
      const url = baseUrl.trim();
      if (!url) {
        setError("Base URL is required (e.g. https://store.com).");
        setLoading(false);
        return;
      }
      payload.base_url = url;
      if (displayName.trim()) payload.display_name = displayName.trim();
    }
    payload.price_premium_percent = pricePremiumPercent;
    payload.available_to_customize = availableToCustomize;
    if (accessToken.trim()) payload.access_token = accessToken.trim();

    try {
      const res = await fetch("/api/platform/ucp-partners", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error((data as { detail?: string }).detail || "Failed to add UCP partner");
      }

      setSuccess({
        registry_id: (data as { registry_id?: string }).registry_id,
        base_url: (data as { base_url?: string }).base_url,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950 p-4 max-w-md">
        <p className="font-medium text-green-800 dark:text-green-200">UCP partner added successfully.</p>
        <p className="text-sm text-green-700 dark:text-green-300 mt-1">
          Base URL: {success.base_url}
          {success.registry_id && ` · ID: ${success.registry_id.slice(0, 8)}…`}
        </p>
        <div className="mt-4 flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href="/platform/partners/ucp">Back to UCP Partners</Link>
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setSuccess(null);
              setBaseUrl("");
              setDisplayName("");
              setManifestJson("");
              setPricePremiumPercent(0);
              setAvailableToCustomize(false);
              setAccessToken("");
            }}
          >
            Add another
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="max-w-md space-y-4">
      <div className="flex gap-4 border-b border-[rgb(var(--color-border))] pb-2">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="mode"
            checked={mode === "manual"}
            onChange={() => setMode("manual")}
            className="rounded"
          />
          <span className="text-sm font-medium">Enter details manually</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name="mode"
            checked={mode === "manifest"}
            onChange={() => setMode("manifest")}
            className="rounded"
          />
          <span className="text-sm font-medium">Paste manifest (JSON)</span>
        </label>
      </div>

      {mode === "manual" ? (
        <>
          <div>
            <label htmlFor="base_url" className="block text-sm font-medium mb-1">
              Base URL *
            </label>
            <input
              id="base_url"
              type="url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://store.com"
              required={mode === "manual"}
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
            />
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
              Discovery will fetch /.well-known/ucp.json from this origin.
            </p>
          </div>
          <div>
            <label htmlFor="display_name_manual" className="block text-sm font-medium mb-1">
              Display name
            </label>
            <input
              id="display_name_manual"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="My Store"
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
            />
          </div>
        </>
      ) : (
        <>
          <div>
            <label htmlFor="manifest_json" className="block text-sm font-medium mb-1">
              UCP manifest JSON *
            </label>
            <textarea
              id="manifest_json"
              value={manifestJson}
              onChange={(e) => setManifestJson(e.target.value)}
              placeholder='{"ucp":{"services":{"dev.ucp.shopping":{"rest":{"endpoint":"https://store.com/api/v1/ucp"}}}}}'
              rows={8}
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] font-mono text-sm"
            />
            <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
              Base URL is derived from <code className="bg-black/10 px-1 rounded">ucp.services[&quot;dev.ucp.shopping&quot;].rest.endpoint</code>. You can optionally set base URL or display name below to override.
            </p>
          </div>
          <div>
            <label htmlFor="base_url_override" className="block text-sm font-medium mb-1">
              Base URL override (optional)
            </label>
            <input
              id="base_url_override"
              type="url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://store.com"
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
            />
          </div>
          <div>
            <label htmlFor="display_name_manifest" className="block text-sm font-medium mb-1">
              Display name (optional)
            </label>
            <input
              id="display_name_manifest"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="My Store"
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
            />
          </div>
        </>
      )}

      <div className="space-y-4 border-t border-[rgb(var(--color-border))] pt-4">
        <div>
          <label htmlFor="price_premium" className="block text-sm font-medium mb-1">
            Price premium (%)
          </label>
          <input
            id="price_premium"
            type="number"
            min={0}
            step={0.01}
            value={pricePremiumPercent}
            onChange={(e) => setPricePremiumPercent(Number(e.target.value))}
            className="w-full max-w-[120px] px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
          />
          <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
            Optional markup applied to products from this partner (0 = no premium).
          </p>
        </div>
        <div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={availableToCustomize}
              onChange={(e) => setAvailableToCustomize(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm font-medium">Available to customize (design chat)</span>
          </label>
          <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1 ml-6">
            Partner supports customization / design chat.
          </p>
        </div>
        <div>
          <label htmlFor="access_token" className="block text-sm font-medium mb-1">
            Access token (optional)
          </label>
          <input
            id="access_token"
            type="password"
            value={accessToken}
            onChange={(e) => setAccessToken(e.target.value)}
            placeholder="Leave blank if not required"
            className="w-full max-w-md px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
          />
          <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
            Stored securely; used when calling this partner&apos;s API if required.
          </p>
        </div>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div className="flex gap-2">
        <Button type="submit" disabled={loading}>
          {loading ? "Adding..." : "Add UCP partner"}
        </Button>
        <Button type="button" variant="outline" asChild>
          <Link href="/platform/partners/ucp">Cancel</Link>
        </Button>
      </div>
    </form>
  );
}
