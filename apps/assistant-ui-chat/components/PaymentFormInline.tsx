"use client";

import { useState } from "react";

/**
 * Redirect-based payment: fetches Stripe Checkout URL and redirects.
 * No client-side Stripe.js / Payment Element needed.
 */
export function PaymentFormInline({
  orderId,
  onSuccess,
}: {
  orderId: string;
  onSuccess?: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePay = async () => {
    setError(null);
    setLoading(true);
    try {
      const origin =
        typeof window !== "undefined" ? window.location.origin : "";
      const pathname =
        typeof window !== "undefined" ? window.location.pathname : "/";
      const successUrl = `${origin}${pathname}?payment_success=1&order_id=${orderId}`;
      const cancelUrl = `${origin}${pathname}`;

      const res = await fetch("/api/payment/checkout-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: orderId,
          success_url: successUrl,
          cancel_url: cancelUrl,
        }),
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.error || data.detail || "Failed to create checkout");
      }

      const url = data.url;
      if (url && typeof url === "string") {
        window.location.href = url;
        onSuccess?.();
      } else {
        throw new Error("No checkout URL returned");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Payment failed");
      setLoading(false);
    }
  };

  return (
    <div className="my-3 rounded-lg border border-[var(--border)] bg-[var(--card)] p-4 shadow-sm">
      <p className="mb-3 text-sm font-medium text-[var(--foreground)]">
        Order {orderId.slice(0, 8)}…
      </p>
      {error && (
        <div className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
          {error}
        </div>
      )}
      <button
        type="button"
        onClick={handlePay}
        disabled={loading}
        className="w-full rounded-lg bg-[var(--primary)] px-4 py-3 text-sm font-medium text-[var(--primary-foreground)] disabled:opacity-50 hover:opacity-90"
      >
        {loading ? "Redirecting…" : "Pay with card"}
      </button>
      <p className="mt-2 text-xs text-[var(--muted-foreground)]">
        You’ll be redirected to Stripe to complete payment.
      </p>
    </div>
  );
}
