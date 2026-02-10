"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";
import { AddProductDialog } from "./add-product-dialog";

type Product = {
  id: string;
  name: string;
  description: string | null;
  price: number;
  currency: string;
  product_type?: string;
  unit?: string;
  is_available?: boolean;
};

export function ProductsList() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);

  async function fetchProducts() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/products");
      if (res.status === 403) {
        setError("PARTNER_REQUIRED");
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to load products");
      }
      const data = await res.json();
      setProducts(data.products ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchProducts();
  }, []);

  async function handleDelete(id: string) {
    if (!confirm("Delete this product?")) return;
    try {
      const res = await fetch(`/api/products/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete");
      setProducts((p) => p.filter((x) => x.id !== id));
    } catch {
      setError("Failed to delete");
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (error === "PARTNER_REQUIRED") return <PartnerRequiredMessage />;
  if (error) return <p className="text-[rgb(var(--color-error))]">{error}</p>;

  return (
    <PartnerGuard>
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-[rgb(var(--color-text-secondary))]">
          {products.length} product{products.length !== 1 ? "s" : ""}
        </p>
        <Button onClick={() => setAddOpen(true)}>Add Product</Button>
      </div>

      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-[rgb(var(--color-surface))]">
            <tr>
              <th className="text-left px-4 py-2">Name</th>
              <th className="text-left px-4 py-2">Type</th>
              <th className="text-left px-4 py-2">Description</th>
              <th className="text-right px-4 py-2">Price</th>
              <th className="w-24 px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id} className="border-t border-[rgb(var(--color-border))]">
                <td className="px-4 py-2">{p.name}</td>
                <td className="px-4 py-2 text-[rgb(var(--color-text-secondary))]">
                  {(p.product_type === "service" ? "Service" : "Product") + (p.unit ? ` / ${p.unit}` : "")}
                </td>
                <td className="px-4 py-2 text-[rgb(var(--color-text-secondary))]">
                  {p.description || "—"}
                </td>
                <td className="px-4 py-2 text-right">
                  {p.currency} {Number(p.price).toFixed(2)}
                  {p.unit && p.unit !== "piece" && (
                    <span className="text-[rgb(var(--color-text-secondary))] text-sm"> / {p.unit}</span>
                  )}
                </td>
                <td className="px-4 py-2">
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      asChild
                    >
                      <a href={`/products/${p.id}`}>Edit</a>
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(p.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {products.length === 0 && (
          <p className="px-4 py-8 text-center text-[rgb(var(--color-text-secondary))]">
            No products yet. Add one to get started.
          </p>
        )}
      </div>

      <AddProductDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onSuccess={() => {
          setAddOpen(false);
          fetchProducts();
        }}
      />
    </div>
    </PartnerGuard>
  );
}
