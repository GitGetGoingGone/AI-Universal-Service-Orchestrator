"use client";

import { useEffect, useState } from "react";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";
import { Button } from "@/components/ui/button";

type InvItem = {
  product_id: string;
  product_name: string;
  is_available: boolean;
  quantity: number;
  low_stock_threshold: number;
  auto_unlist_when_zero: boolean;
};

export function InventoryList() {
  const [items, setItems] = useState<InvItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchInventory() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/inventory");
      if (res.status === 403) {
        setError("PARTNER_REQUIRED");
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to load");
      }
      const data = await res.json();
      setItems(data.inventory ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchInventory();
  }, []);

  async function updateStock(
    productId: string,
    field: "quantity" | "low_stock_threshold" | "auto_unlist_when_zero",
    value: number | boolean
  ) {
    try {
      const item = items.find((i) => i.product_id === productId);
      const res = await fetch(`/api/inventory/${productId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          quantity: item?.quantity ?? 0,
          low_stock_threshold: item?.low_stock_threshold ?? 5,
          auto_unlist_when_zero: item?.auto_unlist_when_zero ?? true,
          [field]: value,
        }),
      });
      if (!res.ok) throw new Error("Failed");
      fetchInventory();
    } catch {
      setError("Failed to update");
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (error === "PARTNER_REQUIRED") return <PartnerRequiredMessage />;
  if (error) return <p className="text-[rgb(var(--color-error))]">{error}</p>;

  return (
    <PartnerGuard>
      <div className="space-y-4">
        <p className="text-sm text-[rgb(var(--color-text-secondary))]">
          Stock levels, low-stock alerts, auto-unlist when zero.
        </p>
        <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-[rgb(var(--color-surface))]">
              <tr>
                <th className="text-left px-4 py-2">Product</th>
                <th className="text-left px-4 py-2">Quantity</th>
                <th className="text-left px-4 py-2">Low Stock At</th>
                <th className="text-left px-4 py-2">Auto-unlist at 0</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.product_id}
                  className={`border-t border-[rgb(var(--color-border))] ${
                    item.quantity <= item.low_stock_threshold ? "bg-amber-50/50 dark:bg-amber-950/20" : ""
                  }`}
                >
                  <td className="px-4 py-2">{item.product_name}</td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      min="0"
                      value={item.quantity}
                      onChange={(e) =>
                        updateStock(item.product_id, "quantity", Number(e.target.value))
                      }
                      className="w-20 px-2 py-1 rounded border border-[rgb(var(--color-border))]"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="number"
                      min="0"
                      value={item.low_stock_threshold}
                      onChange={(e) =>
                        updateStock(
                          item.product_id,
                          "low_stock_threshold",
                          Number(e.target.value)
                        )
                      }
                      className="w-20 px-2 py-1 rounded border border-[rgb(var(--color-border))]"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="checkbox"
                      checked={item.auto_unlist_when_zero}
                      onChange={(e) =>
                        updateStock(item.product_id, "auto_unlist_when_zero", e.target.checked)
                      }
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length === 0 && (
            <p className="px-4 py-8 text-center text-[rgb(var(--color-text-secondary))]">
              No products. Add products first.
            </p>
          )}
        </div>
      </div>
    </PartnerGuard>
  );
}
