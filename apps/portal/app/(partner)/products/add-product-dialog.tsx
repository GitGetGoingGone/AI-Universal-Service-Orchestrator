"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

const UNIT_OPTIONS = [
  { value: "piece", label: "per piece (pc)", forTypes: ["product", "service"] },
  { value: "hour", label: "per hour", forTypes: ["service"] },
  { value: "day", label: "per day", forTypes: ["service"] },
  { value: "session", label: "per session", forTypes: ["service"] },
  { value: "kg", label: "per kg", forTypes: ["product"] },
  { value: "box", label: "per box", forTypes: ["product"] },
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

type Props = {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

export function AddProductDialog({ open, onClose, onSuccess }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [productType, setProductType] = useState<"product" | "service">("product");

  const unitsForType = UNIT_OPTIONS.filter((u) => u.forTypes.includes(productType));

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const form = e.currentTarget;
    const formData = new FormData(form);

    const targetCountriesRaw = formData.get("target_countries");
    const target_countries =
      typeof targetCountriesRaw === "string" && targetCountriesRaw.trim()
        ? targetCountriesRaw.split(",").map((s) => s.trim()).filter(Boolean)
        : undefined;

    try {
      const res = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.get("name"),
          description: formData.get("description") || undefined,
          price: Number(formData.get("price")),
          product_type: productType,
          unit: formData.get("unit") || (productType === "service" ? "hour" : "piece"),
          url: formData.get("url") || undefined,
          brand: formData.get("brand") || undefined,
          image_url: formData.get("image_url") || undefined,
          is_eligible_search: formData.get("is_eligible_search") === "on",
          is_eligible_checkout: formData.get("is_eligible_checkout") === "on",
          availability: formData.get("availability") || undefined,
          target_countries: target_countries?.length ? target_countries : undefined,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed");
      }

      onSuccess();
      form.reset();
      setProductType("product");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-[rgb(var(--color-background))] rounded-lg p-6 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Add Product or Service</h2>
        <p className="text-xs text-[rgb(var(--color-text-secondary))] mb-4">
          Only name and price are required. Other fields are optional; if required for AI catalog push are missing, push will fail validation.
        </p>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Type</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="productType"
                  checked={productType === "product"}
                  onChange={() => setProductType("product")}
                  className="rounded"
                />
                Product (e.g. bouquet, meal)
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="productType"
                  checked={productType === "service"}
                  onChange={() => setProductType("service")}
                  className="rounded"
                />
                Service (e.g. limo, massage)
              </label>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Name *</label>
            <input
              name="name"
              type="text"
              required
              placeholder={productType === "service" ? "e.g. Limo rental" : "e.g. Bouquet"}
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              name="description"
              rows={2}
              className={inputClass}
            />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium mb-1">Price (USD) *</label>
              <input
                name="price"
                type="number"
                step="0.01"
                min="0"
                required
                className={inputClass}
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium mb-1">Unit</label>
              <select name="unit" className={inputClass} defaultValue={productType === "service" ? "hour" : "piece"}>
                {unitsForType.map((u) => (
                  <option key={u.value} value={u.value}>
                    {u.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Product URL (optional)</label>
            <input name="url" type="url" className={inputClass} placeholder="https://..." />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Brand (optional)</label>
            <input name="brand" type="text" maxLength={70} className={inputClass} placeholder="Brand name" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Image URL (optional)</label>
            <input name="image_url" type="url" className={inputClass} placeholder="https://..." />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Availability (optional)</label>
            <select name="availability" className={inputClass} defaultValue="in_stock">
              {AVAILABILITY_OPTIONS.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Target countries (optional, comma-separated)</label>
            <input
              name="target_countries"
              type="text"
              className={inputClass}
              placeholder="e.g. US, CA, GB"
            />
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" name="is_eligible_search" defaultChecked className="rounded" />
              <span className="text-sm">Eligible for search (AI discovery)</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" name="is_eligible_checkout" className="rounded" />
              <span className="text-sm">Eligible for checkout</span>
            </label>
          </div>
          <p className="text-xs text-[rgb(var(--color-text-secondary))]">
            You can add add-ons after saving — edit the product and use the Addons section.
          </p>
          {error && <p className="text-sm text-[rgb(var(--color-error))]">{error}</p>}
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Adding..." : "Add"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
