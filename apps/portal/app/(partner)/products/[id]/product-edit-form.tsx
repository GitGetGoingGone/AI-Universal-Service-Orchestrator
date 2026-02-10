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
  });

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
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
            />
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium mb-1">Unit</label>
            <select
              value={form.unit}
              onChange={(e) => setForm((f) => ({ ...f, unit: e.target.value }))}
              className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
            >
              {UNIT_OPTIONS.map((u) => (
                <option key={u.value} value={u.value}>
                  {u.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </Button>
      </form>

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
