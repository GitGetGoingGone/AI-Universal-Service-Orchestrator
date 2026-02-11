"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

const inputClass =
  "w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]";

type PartnerCommerce = {
  business_name?: string;
  seller_name?: string;
  seller_url?: string;
  return_policy_url?: string;
  privacy_policy_url?: string;
  terms_url?: string;
  store_country?: string;
  target_countries?: string[] | string;
};

export function CommerceProfileForm() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [validating, setValidating] = useState(false);
  const [partnerValidation, setPartnerValidation] = useState<{
    acp?: { valid: boolean; errors: string[]; warnings: string[] };
  } | null>(null);
  const [form, setForm] = useState<PartnerCommerce>({
    business_name: "",
    seller_name: "",
    seller_url: "",
    return_policy_url: "",
    privacy_policy_url: "",
    terms_url: "",
    store_country: "",
    target_countries: "",
  });

  useEffect(() => {
    fetch("/api/partners/me")
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("Failed"))))
      .then((data) => {
        const p = data.partner ?? {};
        const tc = p.target_countries;
        setForm({
          business_name: p.business_name ?? "",
          seller_name: p.seller_name ?? "",
          seller_url: p.seller_url ?? "",
          return_policy_url: p.return_policy_url ?? "",
          privacy_policy_url: p.privacy_policy_url ?? "",
          terms_url: p.terms_url ?? "",
          store_country: p.store_country ?? "",
          target_countries: Array.isArray(tc) ? tc.join(", ") : typeof tc === "string" ? tc : "",
        });
      })
      .catch(() => setError("Could not load partner profile"))
      .finally(() => setLoading(false));
  }, []);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const target_countries = typeof form.target_countries === "string"
        ? form.target_countries.split(",").map((s) => s.trim()).filter(Boolean)
        : form.target_countries;
      const res = await fetch("/api/partners/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_name: form.business_name || undefined,
          seller_name: form.seller_name || undefined,
          seller_url: form.seller_url || undefined,
          return_policy_url: form.return_policy_url || undefined,
          privacy_policy_url: form.privacy_policy_url || undefined,
          terms_url: form.terms_url || undefined,
          store_country: form.store_country || undefined,
          target_countries: target_countries?.length ? target_countries : undefined,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to save");
      }
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (error && !form.seller_name && !form.business_name)
    return <p className="text-[rgb(var(--color-error))]">{error}</p>;

  return (
    <form onSubmit={onSubmit} className="max-w-lg space-y-4">
      <p className="text-sm text-[rgb(var(--color-text-secondary))]">
        Used for ChatGPT and Gemini discovery. Fill in your store and policy URLs so products can be surfaced correctly.
      </p>
      {error && <p className="text-sm text-[rgb(var(--color-error))]">{error}</p>}
      {success && <p className="text-sm text-green-600">Saved.</p>}
      <div>
        <label className="block text-sm font-medium mb-1">Business name</label>
        <input
          value={form.business_name ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, business_name: e.target.value }))}
          type="text"
          className={inputClass}
          placeholder="Your business or brand name"
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Seller name (display)</label>
        <input
          value={form.seller_name ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, seller_name: e.target.value }))}
          type="text"
          className={inputClass}
          placeholder="Name shown in AI catalogs (defaults to business name)"
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Seller URL</label>
        <input
          value={form.seller_url ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, seller_url: e.target.value }))}
          type="url"
          className={inputClass}
          placeholder="https://..."
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Return policy URL</label>
        <input
          value={form.return_policy_url ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, return_policy_url: e.target.value }))}
          type="url"
          className={inputClass}
          placeholder="https://..."
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Privacy policy URL</label>
        <input
          value={form.privacy_policy_url ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, privacy_policy_url: e.target.value }))}
          type="url"
          className={inputClass}
          placeholder="https://..."
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Terms of service URL</label>
        <input
          value={form.terms_url ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, terms_url: e.target.value }))}
          type="url"
          className={inputClass}
          placeholder="https://..."
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Store country (ISO 3166-1 alpha-2)</label>
        <input
          value={form.store_country ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, store_country: e.target.value }))}
          type="text"
          maxLength={2}
          className={inputClass}
          placeholder="e.g. US"
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Target countries (comma-separated)</label>
        <input
          value={typeof form.target_countries === "string" ? form.target_countries : (Array.isArray(form.target_countries) ? form.target_countries.join(", ") : "")}
          onChange={(e) => setForm((f) => ({ ...f, target_countries: e.target.value }))}
          type="text"
          className={inputClass}
          placeholder="e.g. US, CA, GB"
        />
      </div>
      <div className="flex gap-3 items-center">
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save commerce profile"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={validating}
          onClick={async () => {
            setValidating(true);
            setPartnerValidation(null);
            try {
              const res = await fetch("/api/partners/me/validate-discovery");
              const data = await res.json().catch(() => ({}));
              if (res.ok) setPartnerValidation({ acp: data.acp });
              else setPartnerValidation({ acp: { valid: false, errors: [data.detail || "Validation failed"], warnings: [] } });
            } catch {
              setPartnerValidation({ acp: { valid: false, errors: ["Request failed"], warnings: [] } });
            } finally {
              setValidating(false);
            }
          }}
        >
          {validating ? "Validating..." : "Validate for discovery"}
        </Button>
      </div>
      {partnerValidation?.acp && (
        <div className="mt-4 p-3 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] text-sm">
          <span className="font-medium">ChatGPT (ACP) seller profile: </span>
          {partnerValidation.acp.valid ? (
            <span className="text-green-600">Ready for discovery</span>
          ) : (
            <span className="text-[rgb(var(--color-error))]">Not ready</span>
          )}
          {partnerValidation.acp.errors?.length > 0 && (
            <ul className="list-disc ml-4 mt-1 text-[rgb(var(--color-error))]">
              {partnerValidation.acp.errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </form>
  );
}
