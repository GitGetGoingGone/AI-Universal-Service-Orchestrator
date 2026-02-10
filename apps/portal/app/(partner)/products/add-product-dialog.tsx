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
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              name="description"
              rows={2}
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
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
                className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium mb-1">Unit</label>
              <select
                name="unit"
                className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
                defaultValue={productType === "service" ? "hour" : "piece"}
              >
                {unitsForType.map((u) => (
                  <option key={u.value} value={u.value}>
                    {u.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <p className="text-xs text-[rgb(var(--color-text-secondary))]">
            You can add add-ons (e.g. extra driver, champagne) after saving — edit the product and
            use the Addons section.
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
