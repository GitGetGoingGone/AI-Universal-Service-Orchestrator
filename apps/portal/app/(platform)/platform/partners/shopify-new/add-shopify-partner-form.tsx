"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export function AddShopifyPartnerForm() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ partner_id?: string; shop_url?: string } | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    const form = e.currentTarget;
    const formData = new FormData(form);

    const shopUrl = (formData.get("shop_url") as string)?.trim();
    const mcpEndpoint = (formData.get("mcp_endpoint") as string)?.trim();
    const displayName = (formData.get("display_name") as string)?.trim();
    const capabilitiesStr = (formData.get("supported_capabilities") as string)?.trim();
    const supported_capabilities = capabilitiesStr
      ? capabilitiesStr.split(",").map((s) => s.trim()).filter(Boolean)
      : [];
    const available_to_customize = (formData.get("available_to_customize") as string) === "on";
    const price_premium_percent = formData.get("price_premium_percent");
    const access_token = (formData.get("access_token") as string)?.trim() || undefined;

    if (!shopUrl || !mcpEndpoint) {
      setError("Shop URL and MCP endpoint are required.");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch("/api/platform/shopify-partners", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          shop_url: shopUrl,
          mcp_endpoint: mcpEndpoint,
          display_name: displayName || shopUrl,
          supported_capabilities,
          available_to_customize,
          price_premium_percent: price_premium_percent ? Number(price_premium_percent) : 0,
          ...(access_token ? { access_token } : {}),
        }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error((data as { detail?: string }).detail || "Failed to add Shopify partner");
      }

      setSuccess({
        partner_id: (data as { partner_id?: string }).partner_id,
        shop_url: (data as { shop_url?: string }).shop_url,
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
        <p className="font-medium text-green-800 dark:text-green-200">Shopify partner added successfully.</p>
        <p className="text-sm text-green-700 dark:text-green-300 mt-1">
          Shop: {success.shop_url}
          {success.partner_id && ` · Partner ID: ${success.partner_id.slice(0, 8)}…`}
        </p>
        <div className="mt-4 flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href="/platform/partners">Back to Partners</Link>
          </Button>
          <Button type="button" size="sm" variant="secondary" onClick={() => setSuccess(null)}>
          Add another
        </Button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="max-w-md space-y-4">
      <div>
        <label htmlFor="shop_url" className="block text-sm font-medium mb-1">
          Shop URL *
        </label>
        <input
          id="shop_url"
          name="shop_url"
          type="text"
          required
          placeholder="mystore.myshopify.com"
          className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        />
      </div>
      <div>
        <label htmlFor="mcp_endpoint" className="block text-sm font-medium mb-1">
          MCP endpoint *
        </label>
        <input
          id="mcp_endpoint"
          name="mcp_endpoint"
          type="url"
          required
          placeholder="https://mystore.com/api/mcp"
          className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        />
      </div>
      <div>
        <label htmlFor="display_name" className="block text-sm font-medium mb-1">
          Display name
        </label>
        <input
          id="display_name"
          name="display_name"
          type="text"
          placeholder="My Store"
          className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        />
      </div>
      <div>
        <label htmlFor="supported_capabilities" className="block text-sm font-medium mb-1">
          Supported capabilities (comma-separated)
        </label>
        <input
          id="supported_capabilities"
          name="supported_capabilities"
          type="text"
          placeholder="search_shop_catalog, get_product_details"
          className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        />
      </div>
      <div>
        <label htmlFor="price_premium_percent" className="block text-sm font-medium mb-1">
          Price premium (%)
        </label>
        <input
          id="price_premium_percent"
          name="price_premium_percent"
          type="number"
          min={0}
          step={0.01}
          defaultValue={0}
          className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        />
      </div>
      <div className="flex items-center gap-2">
        <input
          id="available_to_customize"
          name="available_to_customize"
          type="checkbox"
          className="rounded border-[rgb(var(--color-border))]"
        />
        <label htmlFor="available_to_customize" className="text-sm">
          Available to customize (design chat)
        </label>
      </div>
      <div>
        <label htmlFor="access_token" className="block text-sm font-medium mb-1">
          Access token (optional)
        </label>
        <input
          id="access_token"
          name="access_token"
          type="password"
          autoComplete="off"
          placeholder="Leave blank to add later"
          className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        />
        <p className="text-xs text-[rgb(var(--color-text-secondary))] mt-1">
          Required for Shopify Draft Orders (checkout). Can be added or updated later.
        </p>
      </div>
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <div className="flex gap-2">
        <Button type="submit" disabled={loading}>
          {loading ? "Adding..." : "Add Shopify partner"}
        </Button>
        <Button type="button" variant="outline" asChild>
          <Link href="/platform/partners">Cancel</Link>
        </Button>
      </div>
    </form>
  );
}
