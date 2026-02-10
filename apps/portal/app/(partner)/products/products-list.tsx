"use client";

import { useEffect, useState, useRef } from "react";
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
  last_acp_push_at?: string | null;
  last_acp_push_success?: boolean | null;
  quantity?: number;
  low_stock_threshold?: number;
};

type Promotion = {
  id: string;
  name: string;
  promo_type: string;
  value: number | null;
  product_ids: string[] | null;
};

export function ProductsList() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [pushStatus, setPushStatus] = useState<{ next_acp_push_allowed_at: string | null } | null>(null);
  const [pushing, setPushing] = useState(false);
  const [pushMessage, setPushMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [promotions, setPromotions] = useState<Promotion[]>([]);
  const [applyPromoId, setApplyPromoId] = useState("");
  const [removePromoId, setRemovePromoId] = useState("");
  const [applyingPromo, setApplyingPromo] = useState(false);
  const [removingPromo, setRemovingPromo] = useState(false);
  const selectAllRef = useRef<HTMLInputElement>(null);

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

  function fetchPushStatus() {
    fetch("/api/feeds/push-status")
      .then((res) => (res.ok ? res.json() : { next_acp_push_allowed_at: null }))
      .then((data: { next_acp_push_allowed_at: string | null }) => setPushStatus(data))
      .catch(() => setPushStatus({ next_acp_push_allowed_at: null }));
  }

  useEffect(() => {
    fetchProducts();
    fetchPushStatus();
    fetch("/api/promotions")
      .then((res) => (res.ok ? res.json() : { promotions: [] }))
      .then((data) => setPromotions(data.promotions ?? []))
      .catch(() => setPromotions([]));
  }, []);

  function getPromotionNamesForProduct(productId: string): string[] {
    return promotions.filter((pr) => (pr.product_ids ?? []).includes(productId)).map((pr) => pr.name);
  }

  async function applyPromotionToSelected() {
    if (!applyPromoId || selectedIds.size === 0) return;
    setApplyingPromo(true);
    try {
      const res = await fetch(`/api/promotions/${applyPromoId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ add_product_ids: Array.from(selectedIds) }),
      });
      if (!res.ok) throw new Error("Failed");
      setApplyPromoId("");
      setSelectedIds(new Set());
      fetch("/api/promotions").then((r) => r.json()).then((d) => setPromotions(d.promotions ?? []));
    } catch {
      alert("Failed to apply promotion");
    } finally {
      setApplyingPromo(false);
    }
  }

  async function removePromotionFromSelected() {
    if (!removePromoId || selectedIds.size === 0) return;
    setRemovingPromo(true);
    try {
      const res = await fetch(`/api/promotions/${removePromoId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ remove_product_ids: Array.from(selectedIds) }),
      });
      if (!res.ok) throw new Error("Failed");
      setRemovePromoId("");
      setSelectedIds(new Set());
      fetch("/api/promotions").then((r) => r.json()).then((d) => setPromotions(d.promotions ?? []));
    } catch {
      alert("Failed to remove promotion");
    } finally {
      setRemovingPromo(false);
    }
  }

  useEffect(() => {
    const el = selectAllRef.current;
    if (!el) return;
    const n = selectedIds.size;
    const total = products.length;
    el.indeterminate = n > 0 && n < total;
  }, [selectedIds.size, products.length]);

  const nextAt = pushStatus?.next_acp_push_allowed_at;
  const nextAtDate = nextAt ? new Date(nextAt) : null;
  const chatgptDisabled = !!(nextAtDate && new Date() < nextAtDate);

  async function pushCatalog(targets: ("chatgpt" | "gemini")[], productIds?: string[]) {
    setPushing(true);
    setPushMessage(null);
    const scope = productIds?.length ? "selected" : "all";
    const body = productIds?.length
      ? { scope: "selected" as const, product_ids: productIds, targets }
      : { scope: "all" as const, targets };
    try {
      const res = await fetch("/api/feeds/push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 429) {
        setPushMessage({
          type: "error",
          text: data.message || "Rate limited. Try again in 15 minutes.",
        });
        fetchPushStatus();
      } else if (!res.ok) {
        setPushMessage({ type: "error", text: data.detail || "Push failed" });
      } else {
        setPushMessage({ type: "success", text: "Push completed." });
        fetchPushStatus();
        fetchProducts();
        if (productIds?.length) setSelectedIds(new Set());
      }
    } catch {
      setPushMessage({ type: "error", text: "Request failed" });
    } finally {
      setPushing(false);
    }
  }

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
    <div className="space-y-6">
      {/* Push catalog (AI discovery) */}
      <section className="p-4 rounded-lg border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))]">
        <h2 className="text-lg font-semibold mb-2">Push to AI catalog</h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-3">
          Push your catalog to ChatGPT and/or Gemini so products can be discovered in AI assistants.
        </p>
        {chatgptDisabled && nextAt && (
          <p className="text-amber-600 text-sm mb-2">
            ChatGPT: next update at {new Date(nextAt).toLocaleString()} (15-min limit).
          </p>
        )}
        {pushMessage && (
          <p className={`text-sm mb-2 ${pushMessage.type === "success" ? "text-green-600" : "text-[rgb(var(--color-error))]"}`}>
            {pushMessage.text}
          </p>
        )}
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-2">
          Select products below to push only those, or push entire catalog.
        </p>
        <div className="flex flex-wrap gap-2 items-center">
          <Button onClick={() => pushCatalog(["chatgpt"])} disabled={pushing || chatgptDisabled}>
            {pushing ? "Pushing..." : "Push all to ChatGPT"}
          </Button>
          <Button variant="outline" onClick={() => pushCatalog(["gemini"])} disabled={pushing}>
            Push all to Gemini
          </Button>
          <Button variant="outline" onClick={() => pushCatalog(["chatgpt", "gemini"])} disabled={pushing || chatgptDisabled}>
            Push all to both
          </Button>
          {selectedIds.size > 0 && (
            <>
              <span className="text-sm text-[rgb(var(--color-text-secondary))]">|</span>
              <Button onClick={() => pushCatalog(["chatgpt"], Array.from(selectedIds))} disabled={pushing || chatgptDisabled}>
                Push {selectedIds.size} selected to ChatGPT
              </Button>
              <Button variant="outline" onClick={() => pushCatalog(["gemini"], Array.from(selectedIds))} disabled={pushing}>
                Push {selectedIds.size} selected to Gemini
              </Button>
              <Button variant="outline" onClick={() => pushCatalog(["chatgpt", "gemini"], Array.from(selectedIds))} disabled={pushing || chatgptDisabled}>
                Push {selectedIds.size} selected to both
              </Button>
              <span className="text-sm text-[rgb(var(--color-text-secondary))]">|</span>
              <select
                value={applyPromoId}
                onChange={(e) => setApplyPromoId(e.target.value)}
                className="rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-bg))] px-2 py-1.5 text-sm"
              >
                <option value="">Apply promotion…</option>
                {promotions.map((pr) => (
                  <option key={pr.id} value={pr.id}>{pr.name}</option>
                ))}
              </select>
              <Button
                variant="outline"
                onClick={applyPromotionToSelected}
                disabled={applyingPromo || !applyPromoId}
              >
                {applyingPromo ? "Applying…" : "Apply to selected"}
              </Button>
              <select
                value={removePromoId}
                onChange={(e) => setRemovePromoId(e.target.value)}
                className="rounded border border-[rgb(var(--color-border))] bg-[rgb(var(--color-bg))] px-2 py-1.5 text-sm"
              >
                <option value="">Remove promotion…</option>
                {promotions.map((pr) => (
                  <option key={pr.id} value={pr.id}>{pr.name}</option>
                ))}
              </select>
              <Button
                variant="outline"
                onClick={removePromotionFromSelected}
                disabled={removingPromo || !removePromoId}
              >
                {removingPromo ? "Removing…" : "Remove from selected"}
              </Button>
            </>
          )}
        </div>
      </section>

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
              <th className="w-10 px-4 py-2">
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  checked={products.length > 0 && selectedIds.size === products.length}
                  onChange={() => {
                    if (selectedIds.size === products.length) setSelectedIds(new Set());
                    else setSelectedIds(new Set(products.map((p) => p.id)));
                  }}
                  className="rounded"
                />
              </th>
              <th className="text-left px-4 py-2">Name</th>
              <th className="text-left px-4 py-2">Type</th>
              <th className="text-left px-4 py-2">Stock</th>
              <th className="text-left px-4 py-2">Description</th>
              <th className="text-right px-4 py-2">Price</th>
              <th className="text-left px-4 py-2">Promotions</th>
              <th className="text-left px-4 py-2">Last pushed</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="w-24 px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id} className="border-t border-[rgb(var(--color-border))]">
                <td className="px-4 py-2">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(p.id)}
                    onChange={() => {
                      setSelectedIds((prev) => {
                        const next = new Set(prev);
                        if (next.has(p.id)) next.delete(p.id);
                        else next.add(p.id);
                        return next;
                      });
                    }}
                    className="rounded"
                  />
                </td>
                <td className="px-4 py-2">{p.name}</td>
                <td className="px-4 py-2 text-[rgb(var(--color-text-secondary))]">
                  {(p.product_type === "service" ? "Service" : "Product") + (p.unit ? ` / ${p.unit}` : "")}
                </td>
                <td className="px-4 py-2 text-[rgb(var(--color-text-secondary))]">
                  {p.quantity != null ? p.quantity : "—"}
                  {p.low_stock_threshold != null && p.quantity != null && p.quantity <= p.low_stock_threshold && p.quantity > 0 && (
                    <span className="text-amber-600 ml-1">(low)</span>
                  )}
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
                <td className="px-4 py-2 text-[rgb(var(--color-text-secondary))] text-sm">
                  {getPromotionNamesForProduct(p.id).length ? getPromotionNamesForProduct(p.id).join(", ") : "—"}
                </td>
                <td className="px-4 py-2 text-[rgb(var(--color-text-secondary))] text-sm">
                  {p.last_acp_push_at ? new Date(p.last_acp_push_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-2 text-sm">
                  {p.last_acp_push_at == null ? "—" : p.last_acp_push_success ? (
                    <span className="text-green-600">Success</span>
                  ) : (
                    <span className="text-[rgb(var(--color-error))]">Failed</span>
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
