"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

const inputClass =
  "w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]";

type Props = { productId: string };

type InventoryData = {
  quantity?: number;
  low_stock_threshold?: number;
  auto_unlist_when_zero?: boolean;
};

export function ProductInventorySection({ productId }: Props) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [quantity, setQuantity] = useState(0);
  const [lowStockThreshold, setLowStockThreshold] = useState(5);
  const [autoUnlistWhenZero, setAutoUnlistWhenZero] = useState(true);

  useEffect(() => {
    fetch(`/api/inventory/${productId}`)
      .then((res) => (res.ok ? res.json() : Promise.resolve({} as InventoryData)))
      .then((data: InventoryData) => {
        setQuantity(data.quantity ?? 0);
        setLowStockThreshold(data.low_stock_threshold ?? 5);
        setAutoUnlistWhenZero(data.auto_unlist_when_zero !== false);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [productId]);

  async function save() {
    setSaving(true);
    try {
      const res = await fetch(`/api/inventory/${productId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          quantity,
          low_stock_threshold: lowStockThreshold,
          auto_unlist_when_zero: autoUnlistWhenZero,
        }),
      });
      if (!res.ok) throw new Error("Failed");
    } catch {
      alert("Failed to save inventory");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="text-sm text-[rgb(var(--color-text-secondary))]">Loading inventory...</p>;

  return (
    <section className="border-t border-[rgb(var(--color-border))] pt-6 mt-6">
      <h3 className="font-semibold mb-2">Inventory</h3>
      <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-3">
        Stock level, low-stock threshold, and auto-unlist when out of stock.
      </p>
      <div className="max-w-md space-y-3">
        <div>
          <label className="block text-sm font-medium mb-1">Quantity in stock</label>
          <input
            type="number"
            min={0}
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Low stock at (alert threshold)</label>
          <input
            type="number"
            min={0}
            value={lowStockThreshold}
            onChange={(e) => setLowStockThreshold(Number(e.target.value))}
            className={inputClass}
          />
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={autoUnlistWhenZero}
            onChange={(e) => setAutoUnlistWhenZero(e.target.checked)}
            className="rounded"
          />
          Auto-unlist when quantity is 0
        </label>
        <Button onClick={save} disabled={saving}>
          {saving ? "Saving..." : "Save inventory"}
        </Button>
      </div>
    </section>
  );
}
