"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

const UNIT_OPTIONS = [
  { value: "piece", label: "per piece (pc)" },
  { value: "hour", label: "per hour" },
  { value: "day", label: "per day" },
  { value: "session", label: "per session" },
  { value: "kg", label: "per kg" },
  { value: "box", label: "per box" },
];

const AVAILABILITY_OPTIONS = [
  { value: "in_stock", label: "In stock" },
  { value: "out_of_stock", label: "Out of stock" },
  { value: "pre_order", label: "Pre-order" },
  { value: "backorder", label: "Backorder" },
  { value: "unknown", label: "Unknown" },
];

const inputClass =
  "w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]";

type Addon = { id: string; name: string; price_delta: number; is_required: boolean };

type Props = { productId: string };

export function ProductEditForm({ productId }: Props) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addons, setAddons] = useState<Addon[]>([]);
  const [addonName, setAddonName] = useState("");
  const [addonPrice, setAddonPrice] = useState("");
  const [addingAddon, setAddingAddon] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    price: "",
    product_type: "product" as "product" | "service",
    unit: "piece",
    url: "",
    brand: "",
    image_url: "",
    is_eligible_search: true,
    is_eligible_checkout: false,
    availability: "in_stock" as string,
  });
  const [validation, setValidation] = useState<{
    acp?: { valid: boolean; errors: string[]; warnings: string[] };
    ucp?: { valid: boolean; errors: string[] };
  } | null>(null);
  const [validating, setValidating] = useState(false);

  function fetchProduct() {
    fetch(`/api/products/${productId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Not found");
        return res.json();
      })
      .then((data) => {
        setForm({
          name: data.name || "",
          description: data.description || "",
          price: String(data.price ?? ""),
          product_type: data.product_type === "service" ? "service" : "product",
          unit: data.unit || "piece",
          url: data.url ?? "",
          brand: data.brand ?? "",
          image_url: data.image_url ?? "",
          is_eligible_search: data.is_eligible_search !== false,
          is_eligible_checkout: !!data.is_eligible_checkout,
          availability: data.availability ?? "in_stock",
        });
      })
      .catch(() => setError("Product not found"))
      .finally(() => setLoading(false));
  }

  function fetchAddons() {
    fetch(`/api/products/${productId}/addons`)
      .then((res) => res.ok ? res.json() : { addons: [] })
      .then((data) => setAddons(data.addons ?? []))
      .catch(() => setAddons([]));
  }

  useEffect(() => {
    fetchProduct();
    fetchAddons();
  }, [productId]);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const res = await fetch(`/api/products/${productId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name,
          description: form.description || null,
          price: Number(form.price),
          product_type: form.product_type,
          unit: form.unit,
          url: form.url || null,
          brand: form.brand || null,
          image_url: form.image_url || null,
          is_eligible_search: form.is_eligible_search,
          is_eligible_checkout: form.is_eligible_checkout,
          availability: form.availability,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed");
      }

      router.push("/products");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  async function addAddon() {
    if (!addonName.trim()) return;
    setAddingAddon(true);
    try {
      const res = await fetch(`/api/products/${productId}/addons`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: addonName.trim(),
          price_delta: Number(addonPrice) || 0,
          is_required: false,
        }),
      });
      if (!res.ok) throw new Error("Failed");
      setAddonName("");
      setAddonPrice("");
      fetchAddons();
    } catch {
      alert("Failed to add addon");
    } finally {
      setAddingAddon(false);
    }
  }

  async function removeAddon(addonId: string) {
    if (!confirm("Remove this addon?")) return;
    try {
      const res = await fetch(`/api/products/${productId}/addons/${addonId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed");
      fetchAddons();
    } catch {
      alert("Failed to remove addon");
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (error) return <p className="text-[rgb(var(--color-error))]">{error}</p>;

  return (
    <div className="space-y-8">
      <form onSubmit={onSubmit} className="max-w-md space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Type</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={form.product_type === "product"}
                onChange={() => setForm((f) => ({ ...f, product_type: "product" }))}
                className="rounded"
              />
              Product
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={form.product_type === "service"}
                onChange={() => setForm((f) => ({ ...f, product_type: "service" }))}
                className="rounded"
              />
              Service
            </label>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Name *</label>
          <input
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            type="text"
            required
            className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            rows={3}
            className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
          />
        </div>
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="block text-sm font-medium mb-1">Price (USD) *</label>
            <input
              value={form.price}
              onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))}
              type="number"
              step="0.01"
              min="0"
              required
              className={inputClass}
            />
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium mb-1">Unit</label>
            <select
              value={form.unit}
              onChange={(e) => setForm((f) => ({ ...f, unit: e.target.value }))}
              className={inputClass}
            >
              {UNIT_OPTIONS.map((u) => (
                <option key={u.value} value={u.value}>
                  {u.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Product URL</label>
          <input
            value={form.url}
            onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
            type="url"
            className={inputClass}
            placeholder="https://..."
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Brand</label>
          <input
            value={form.brand}
            onChange={(e) => setForm((f) => ({ ...f, brand: e.target.value }))}
            type="text"
            maxLength={70}
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Image URL</label>
          <input
            value={form.image_url}
            onChange={(e) => setForm((f) => ({ ...f, image_url: e.target.value }))}
            type="url"
            className={inputClass}
            placeholder="https://..."
          />
        </div>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.is_eligible_search}
              onChange={(e) => setForm((f) => ({ ...f, is_eligible_search: e.target.checked }))}
              className="rounded"
            />
            Eligible for search (AI discovery)
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.is_eligible_checkout}
              onChange={(e) => setForm((f) => ({ ...f, is_eligible_checkout: e.target.checked }))}
              className="rounded"
            />
            Eligible for checkout
          </label>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Availability</label>
          <select
            value={form.availability}
            onChange={(e) => setForm((f) => ({ ...f, availability: e.target.value }))}
            className={inputClass}
          >
            {AVAILABILITY_OPTIONS.map((a) => (
              <option key={a.value} value={a.value}>
                {a.label}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </Button>
      </form>

      <section className="border-t border-[rgb(var(--color-border))] pt-6">
        <h3 className="font-semibold mb-2">Discovery (ChatGPT / Gemini)</h3>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-3">
          Validate this product for AI catalog eligibility. Save the form first so the latest data is checked.
        </p>
        <Button
          type="button"
          variant="outline"
          disabled={validating}
          onClick={async () => {
            setValidating(true);
            setValidation(null);
            try {
              const res = await fetch(`/api/products/${productId}/validate-discovery`);
              const data = await res.json().catch(() => ({}));
              if (res.ok) setValidation({ acp: data.acp, ucp: data.ucp });
              else setValidation({ acp: { valid: false, errors: [data.detail || "Validation failed"], warnings: [] }, ucp: { valid: false, errors: [] } });
            } catch {
              setValidation({ acp: { valid: false, errors: ["Request failed"], warnings: [] }, ucp: { valid: false, errors: [] } });
            } finally {
              setValidating(false);
            }
          }}
        >
          {validating ? "Validating..." : "Validate for discovery"}
        </Button>
        {validation && (
          <div className="mt-4 space-y-2 text-sm">
            {validation.acp && (
              <div>
                <span className="font-medium">ChatGPT (ACP): </span>
                {validation.acp.valid ? (
                  <span className="text-green-600">Ready for ChatGPT</span>
                ) : (
                  <span className="text-[rgb(var(--color-error))]">Not ready</span>
                )}
                {validation.acp.errors?.length > 0 && (
                  <ul className="list-disc ml-4 mt-1 text-[rgb(var(--color-error))]">
                    {validation.acp.errors.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                )}
                {validation.acp.warnings?.length > 0 && (
                  <ul className="list-disc ml-4 mt-1 text-amber-600">
                    {validation.acp.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            {validation.ucp && (
              <div>
                <span className="font-medium">Gemini (UCP): </span>
                {validation.ucp.valid ? (
                  <span className="text-green-600">Ready for Gemini</span>
                ) : (
                  <span className="text-[rgb(var(--color-error))]">Not ready</span>
                )}
                {validation.ucp.errors?.length > 0 && (
                  <ul className="list-disc ml-4 mt-1 text-[rgb(var(--color-error))]">
                    {validation.ucp.errors.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
      </section>

      <section>
        <h3 className="font-semibold mb-2">Add-ons</h3>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-3">
          Optional extras (e.g. champagne for limo, gift wrap for bouquet).
        </p>
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            placeholder="Addon name"
            value={addonName}
            onChange={(e) => setAddonName(e.target.value)}
            className="flex-1 px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
          />
          <input
            type="number"
            step="0.01"
            placeholder="+$"
            value={addonPrice}
            onChange={(e) => setAddonPrice(e.target.value)}
            className="w-24 px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
          />
          <Button type="button" size="sm" onClick={addAddon} disabled={addingAddon || !addonName.trim()}>
            Add
          </Button>
        </div>
        {addons.length > 0 ? (
          <ul className="space-y-2">
            {addons.map((a) => (
              <li
                key={a.id}
                className="flex items-center justify-between py-2 px-3 rounded-md border border-[rgb(var(--color-border))]"
              >
                <span>
                  {a.name}
                  {a.price_delta !== 0 && (
                    <span className="text-[rgb(var(--color-text-secondary))] ml-2">
                      {a.price_delta > 0 ? "+" : "-"}${Math.abs(Number(a.price_delta)).toFixed(2)}
                    </span>
                  )}
                </span>
                <Button type="button" size="sm" variant="outline" onClick={() => removeAddon(a.id)}>
                  Remove
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-[rgb(var(--color-text-secondary))]">No add-ons yet.</p>
        )}
      </section>
    </div>
  );
}
