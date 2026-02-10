"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

type Props = { productId: string };

export function ProductDiscoveryPush({ productId }: Props) {
  const [pushStatus, setPushStatus] = useState<{ next_acp_push_allowed_at: string | null } | null>(null);
  const [pushing, setPushing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/feeds/push-status")
      .then((res) => (res.ok ? res.json() : { next_acp_push_allowed_at: null }))
      .then((data: { next_acp_push_allowed_at: string | null }) => setPushStatus(data))
      .catch(() => setPushStatus({ next_acp_push_allowed_at: null }));
  }, []);

  const nextAt = pushStatus?.next_acp_push_allowed_at;
  const nextAtDate = nextAt ? new Date(nextAt) : null;
  const chatgptDisabled = !!(nextAtDate && new Date() < nextAtDate);

  async function push(targets: ("chatgpt" | "gemini")[]) {
    setPushing(true);
    setMessage(null);
    try {
      const res = await fetch("/api/feeds/push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scope: "single",
          product_id: productId,
          targets,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 429) {
        setMessage(data.message || "Rate limited. Try again in 15 minutes.");
        fetch("/api/feeds/push-status").then((r) => (r.ok ? r.json() : { next_acp_push_allowed_at: null })).then((d: { next_acp_push_allowed_at: string | null }) => setPushStatus(d)).catch(() => {});
      } else if (!res.ok) {
        setMessage(data.detail || "Push failed");
      } else {
        setMessage("Push completed.");
        fetch("/api/feeds/push-status").then((r) => (r.ok ? r.json() : { next_acp_push_allowed_at: null })).then((d: { next_acp_push_allowed_at: string | null }) => setPushStatus(d)).catch(() => {});
      }
    } catch {
      setMessage("Request failed");
    } finally {
      setPushing(false);
    }
  }

  return (
    <section className="border-t border-[rgb(var(--color-border))] pt-6 mt-6">
      <h3 className="font-semibold mb-2">Push to AI catalog</h3>
      <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-3">
        Push this product to ChatGPT and/or Gemini.{" "}
        <Link href="/discovery" className="text-[rgb(var(--color-primary))] hover:underline">
          Push entire catalog
        </Link>
      </p>
      {nextAtDate && new Date() < nextAtDate && (
        <p className="text-amber-600 text-sm mb-2">
          ChatGPT: next update at {nextAtDate.toLocaleString()} (15-min limit).
        </p>
      )}
      {message && <p className="text-sm mb-2 text-[rgb(var(--color-text-secondary))]">{message}</p>}
      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() => push(["chatgpt"])}
          disabled={pushing || chatgptDisabled}
        >
          Push to ChatGPT
        </Button>
        <Button size="sm" variant="outline" onClick={() => push(["gemini"])} disabled={pushing}>
          Push to Gemini
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => push(["chatgpt", "gemini"])}
          disabled={pushing || chatgptDisabled}
        >
          Push to both
        </Button>
      </div>
    </section>
  );
}
