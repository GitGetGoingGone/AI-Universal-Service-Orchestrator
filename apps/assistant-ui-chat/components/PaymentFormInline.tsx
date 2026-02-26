"use client";

import { useState, useEffect } from "react";
import { loadStripe, Stripe } from "@stripe/stripe-js";
import { Elements, PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";

const stripePromise: Promise<Stripe | null> | null =
  typeof window !== "undefined" && process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
    ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY, {
        apiVersion: "2023-10-16",
      })
    : null;

/** Wraps Elements with pre-resolved Stripe instance so useStripe() is available immediately. */
function ElementsWithStripe({
  stripePromise: promise,
  clientSecret,
  orderId,
  amount,
  currency,
  onSuccess,
  onError,
}: {
  stripePromise: Promise<Stripe | null> | null;
  clientSecret: string;
  orderId: string;
  amount: number;
  currency: string;
  onSuccess?: () => void;
  onError: (msg: string) => void;
}) {
  const [stripeInstance, setStripeInstance] = useState<Stripe | null>(null);

  useEffect(() => {
    if (!promise) return;
    promise.then((s) => s && setStripeInstance(s));
  }, [promise]);

  if (!stripeInstance) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/30 p-4 text-sm text-[var(--muted-foreground)]">
        Loading Stripe…
      </div>
    );
  }

  return (
    <Elements
      stripe={stripeInstance}
      options={{
        clientSecret,
        appearance: { theme: "stripe" },
      }}
    >
      <PaymentFormInner
        orderId={orderId}
        amount={amount}
        currency={currency}
        onSuccess={() => onSuccess?.()}
        onError={onError}
      />
    </Elements>
  );
}

function PaymentFormInner({
  orderId,
  amount,
  currency,
  onSuccess,
  onError,
}: {
  orderId: string;
  amount: number;
  currency: string;
  onSuccess: () => void;
  onError: (msg: string) => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const isReady = Boolean(stripe && elements);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;
    setLoading(true);
    try {
      const returnUrl = `${window.location.origin}${window.location.pathname}?payment_success=1&order_id=${orderId}`;
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
    <form onSubmit={handleSubmit} className="space-y-4">
      <PaymentElement options={{ layout: "tabs" }} />
      <button
        type="submit"
        disabled={!isReady || loading}
        className="w-full rounded-lg bg-[var(--primary)] px-4 py-3 text-sm font-medium text-[var(--primary-foreground)] disabled:opacity-50 hover:opacity-90"
      >
        {loading ? "Processing…" : isReady ? `Pay ${currency} ${amount.toFixed(2)}` : "Preparing…"}
      </button>
    </form>
  );
}

export function PaymentFormInline({
  orderId,
  onSuccess,
}: {
  orderId: string;
  onSuccess?: () => void;
}) {
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
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
        Stripe is not configured. Set NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY.
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
        {error}
      </div>
    );
  }

  if (loading || !clientSecret) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/30 p-4 text-sm text-[var(--muted-foreground)]">
        Loading payment form…
      </div>
    );
  }

  return (
    <div className="my-3 rounded-lg border border-[var(--border)] bg-[var(--card)] p-4 shadow-sm">
      <p className="mb-3 text-sm font-medium text-[var(--foreground)]">
        Order {orderId.slice(0, 8)}… — {currency} {amount.toFixed(2)}
      </p>
      <ElementsWithStripe
        stripePromise={stripePromise}
        clientSecret={clientSecret}
        orderId={orderId}
        amount={amount}
        currency={currency}
        onSuccess={() => onSuccess?.()}
        onError={setError}
      />
    </div>
  );
}
