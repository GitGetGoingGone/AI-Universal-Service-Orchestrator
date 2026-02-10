"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type Product = { id: string; name: string };

export default function DiscoveryPage() {
  const [scope, setScope] = useState<"single" | "all">("all");
  const [productId, setProductId] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [pushStatus, setPushStatus] = useState<{ next_acp_push_allowed_at: string | null } | null>(null);
  const [pushing, setPushing] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  function fetchPushStatus() {
    fetch("/api/feeds/push-status")
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => setPushStatus(data))
      .catch(() => setPushStatus({ next_acp_push_allowed_at: null }));
  }

  function fetchProducts() {
    fetch("/api/products")
      .then((res) => (res.ok ? res.json() : []))
      .then((data) => setProducts(Array.isArray(data) ? data : data.products ?? []))
      .catch(() => setProducts([]));
  }

  useEffect(() => {
    fetchPushStatus();
    fetchProducts();
  }, []);

  const nextAt = pushStatus?.next_acp_push_allowed_at;
  const now = typeof Date.now === "function" ? new Date() : null;
  const nextAtDate = nextAt ? new Date(nextAt) : null;
  const chatgptDisabled = nextAtDate && now && now < nextAtDate;

  async function push(targets: ("chatgpt" | "gemini")[]) {
    if (scope === "single" && !productId) {
      setMessage({ type: "error", text: "Select a product when pushing a single product." });
      return;
    }
    setPushing(true);
    setMessage(null);
    try {
      const res = await fetch("/api/feeds/push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scope,
          product_id: scope === "single" ? productId : undefined,
          targets,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 429) {
        setMessage({
          type: "error",
          text: data.message || "Rate limited. " + (data.next_allowed_at ? `Next update at ${data.next_allowed_at}` : ""),
        });
        fetchPushStatus();
      } else if (!res.ok) {
        setMessage({ type: "error", text: data.detail || "Push failed" });
      } else {
        setMessage({ type: "success", text: "Push completed." });
        fetchPushStatus();
      }
    } catch {
      setMessage({ type: "error", text: "Request failed" });
    } finally {
      setPushing(false);
    }
  }

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">AI catalog (Discovery)</h1>
      <p className="text-[rgb(var(--color-text-secondary))] mb-6">
        Push your catalog to ChatGPT and/or Gemini so your products can be discovered in AI assistants.
      </p>

      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Scope</h2>
        <div className="flex gap-4 mb-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              checked={scope === "all"}
              onChange={() => setScope("all")}
              className="rounded"
            />
            Push entire catalog
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              checked={scope === "single"}
              onChange={() => setScope("single")}
              className="rounded"
            />
            Push this product only
          </label>
        </div>
        {scope === "single" && (
          <div>
            <label className="block text-sm font-medium mb-1">Product</label>
            <select
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
              className="w-full max-w-md px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
            >
              <option value="">Select a product</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name || p.id}
                </option>
              ))}
            </select>
          </div>
        )}
      </section>

      {chatgptDisabled && nextAt && (
        <p className="text-amber-600 mb-4">
          ChatGPT catalog can be updated again at {new Date(nextAt).toLocaleString()}. (15-minute limit between pushes.)
        </p>
      )}

      {message && (
        <p className={`mb-4 ${message.type === "success" ? "text-green-600" : "text-[rgb(var(--color-error))]"}`}>
          {message.text}
        </p>
      )}

      <section className="flex flex-wrap gap-3">
        <Button
          onClick={() => push(["chatgpt"])}
          disabled={pushing || chatgptDisabled}
          title={chatgptDisabled ? "Wait 15 minutes between ChatGPT pushes" : undefined}
        >
          {pushing ? "Pushing..." : "Push to ChatGPT"}
        </Button>
        <Button variant="outline" onClick={() => push(["gemini"])} disabled={pushing}>
          Push to Gemini
        </Button>
        <Button
          variant="outline"
          onClick={() => push(["chatgpt", "gemini"])}
          disabled={pushing || chatgptDisabled}
          title={chatgptDisabled ? "ChatGPT is rate limited" : undefined}
        >
          Push to both
        </Button>
      </section>
    </main>
  );
}
