"use client";

import { useState, useEffect, useRef } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";

const STRIPE_KEY = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? "";

/** Poll for stripe/elements (useStripe can stay null initially) then confirm. */
async function waitForStripeAndConfirm(
  getStripe: () => unknown,
  getElements: () => unknown,
  orderId: string
): Promise<{ error?: string }> {
  const returnUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}${window.location.pathname}?payment_success=1&order_id=${orderId}`
      : "";
  for (let i = 0; i < 50; i++) {
    const stripe = getStripe();
    const elements = getElements();
    if (stripe && elements) {
      const { error } = await (stripe as { confirmPayment: (o: unknown) => Promise<{ error?: { message?: string } }> }).confirmPayment({
        elements,
        confirmParams: { return_url: returnUrl, receipt_email: undefined },
      });
      return { error: error?.message };
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  return { error: "Payment form is still loading. Please try again." };
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
  const stripeRef = useRef(stripe);
  const elementsRef = useRef(elements);
  stripeRef.current = stripe;
  elementsRef.current = elements;
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { error } = await waitForStripeAndConfirm(
        () => stripeRef.current,
        () => elementsRef.current,
        orderId
      );
      if (error) onError(error);
      else onSuccess();
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
        disabled={loading}
        className="w-full rounded-lg bg-[var(--primary)] px-4 py-3 text-sm font-medium text-[var(--primary-foreground)] disabled:opacity-50 hover:opacity-90"
      >
        {loading ? "Processing…" : `Pay ${currency} ${amount.toFixed(2)}`}
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
  const [stripePromise, setStripePromise] = useState<ReturnType<typeof loadStripe> | null>(null);
  const loadAttempted = useRef(false);

  useEffect(() => {
    if (!loadAttempted.current && STRIPE_KEY) {
      loadAttempted.current = true;
      setStripePromise(loadStripe(STRIPE_KEY, { apiVersion: "2023-10-16" }));
    }
  }, []);

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

  if (!STRIPE_KEY) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
        Stripe is not configured. Set NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY.
      </div>
    );
  }

  if (!stripePromise) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/30 p-4 text-sm text-[var(--muted-foreground)]">
        Loading Stripe…
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
      <Elements
        stripe={stripePromise}
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
          onError={setError}
        />
      </Elements>
    </div>
  );
}
