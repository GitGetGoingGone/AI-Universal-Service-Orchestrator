"use client";

import { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";

const stripePromise =
  typeof window !== "undefined" && process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
    ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY, {
        apiVersion: "2023-10-16",
      })
    : null;

export type PaymentModalProps = {
  orderId: string;
  threadId?: string | null;
  onClose: () => void;
  onSuccess: () => void;
};

function PaymentFormInner({
  orderId,
  threadId,
  amount,
  currency,
  onSuccess,
  onError,
}: {
  orderId: string;
  threadId?: string | null;
  amount: number;
  currency: string;
  onSuccess: () => void;
  onError: (msg: string) => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;
    setLoading(true);
    try {
      const params = new URLSearchParams({ payment_success: "1", order_id: orderId });
      if (threadId) params.set("thread_id", threadId);
      const returnUrl = `${window.location.origin}${window.location.pathname}?${params.toString()}`;
      const { error } = await stripe.confirmPayment({
        elements,
        confirmParams: {
          return_url: returnUrl,
          receipt_email: undefined,
        },
      });
      if (error) {
        onError(error.message || "Payment failed");
      } else {
        onSuccess();
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : "Payment failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <PaymentElement options={{ layout: "tabs" }} />
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={!stripe || loading}
          className="flex-1 px-4 py-3 rounded-xl bg-[var(--primary-color)] text-[var(--primary-foreground)] font-medium disabled:opacity-50"
        >
          {loading ? "Processing…" : `Pay ${currency} ${amount.toFixed(2)}`}
        </button>
      </div>
    </form>
  );
}

export function PaymentModal({
  orderId,
  threadId,
  onClose,
  onSuccess,
}: PaymentModalProps) {
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [amount, setAmount] = useState(0);
  const [currency, setCurrency] = useState("USD");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/payment/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_id: orderId }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.client_secret) {
          setClientSecret(data.client_secret);
          setAmount(data.amount ?? 0);
          setCurrency(data.currency ?? "USD");
        } else {
          setError(data.error || data.detail || "Failed to create payment");
        }
      })
      .catch(() => setError("Request failed"))
      .finally(() => setLoading(false));
  }, [orderId]);

  if (!stripePromise) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
        <div className="max-w-md w-full rounded-xl bg-[var(--card)] p-6 border border-[var(--border)]">
          <p className="text-amber-500">
            Stripe not configured. Set NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY.
          </p>
          <button
            onClick={onClose}
            className="mt-4 px-4 py-2 rounded-lg bg-[var(--primary-color)] text-[var(--primary-foreground)]"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="max-w-md w-full rounded-xl bg-[var(--card)] p-6 border border-[var(--border)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Complete payment</h2>
          <button
            onClick={onClose}
            className="text-[var(--muted)] hover:text-[var(--foreground)] text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <p className="text-sm text-[var(--muted)] mb-4">
          Order {orderId.slice(0, 8)}... — {currency} {amount.toFixed(2)}
        </p>
        {loading && <p className="text-[var(--muted)]">Loading payment form…</p>}
        {error && (
          <p className="text-red-500 text-sm mb-4">{error}</p>
        )}
        {clientSecret && !loading && (
          <Elements
            stripe={stripePromise}
            options={{
              clientSecret,
              appearance: { theme: "stripe" },
            }}
          >
            <PaymentFormInner
              orderId={orderId}
              threadId={threadId}
              amount={amount}
              currency={currency}
              onSuccess={onSuccess}
              onError={setError}
            />
          </Elements>
        )}
      </div>
    </div>
  );
}
