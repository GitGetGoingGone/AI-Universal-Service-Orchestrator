"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";

const stripePromise = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
  ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY, { apiVersion: "2023-10-16" })
  : null;

const DURATION_OPTIONS = [
  { days: 7, label: "7 days" },
  { days: 14, label: "14 days" },
  { days: 30, label: "30 days" },
];

function SponsorshipPaymentForm({
  amount,
  currency,
  onSuccess,
  onError,
}: {
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
      const { error } = await stripe.confirmPayment({
        elements,
        confirmParams: {
          return_url: `${window.location.origin}/products`,
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
      <button
        type="submit"
        disabled={!stripe || loading}
        className="w-full px-4 py-3 rounded bg-[rgb(var(--color-primary))] text-white font-medium disabled:opacity-50"
      >
        {loading ? "Processing…" : `Pay ${currency} ${amount.toFixed(2)}`}
      </button>
    </form>
  );
}

type Props = { productId: string };

export function ProductSponsorship({ productId }: Props) {
  const [open, setOpen] = useState(false);
  const [durationDays, setDurationDays] = useState(7);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [amount, setAmount] = useState(0);
  const [currency, setCurrency] = useState("USD");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startSponsorship() {
    setLoading(true);
    setError(null);
    setClientSecret(null);
    try {
      const res = await fetch("/api/partners/sponsorship/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, duration_days: durationDays }),
      });
      const data = await res.json();
      if (res.ok && data.client_secret) {
        setClientSecret(data.client_secret);
        setAmount(data.amount ?? 0);
        setCurrency(data.currency ?? "USD");
        setOpen(true);
      } else {
        setError(data.detail || "Failed to create sponsorship");
      }
    } catch {
      setError("Request failed");
    } finally {
      setLoading(false);
    }
  }

  function closeModal() {
    setOpen(false);
    setClientSecret(null);
    setError(null);
  }

  if (!stripePromise) {
    return (
      <section className="border-t border-[rgb(var(--color-border))] pt-6 mt-6">
        <h3 className="font-semibold mb-2">Sponsor this product</h3>
        <p className="text-sm text-amber-600">
          Stripe not configured. Set NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY.
        </p>
      </section>
    );
  }

  return (
    <section className="border-t border-[rgb(var(--color-border))] pt-6 mt-6">
      <h3 className="font-semibold mb-2">Sponsor this product</h3>
      <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-3">
        Boost this product in search results. Choose duration and pay via Stripe.
      </p>
      <div className="flex flex-wrap gap-2 items-center">
        <select
          value={durationDays}
          onChange={(e) => setDurationDays(Number(e.target.value))}
          className="px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        >
          {DURATION_OPTIONS.map((o) => (
            <option key={o.days} value={o.days}>
              {o.label}
            </option>
          ))}
        </select>
        <Button
          size="sm"
          onClick={startSponsorship}
          disabled={loading}
        >
          {loading ? "Loading…" : "Sponsor product"}
        </Button>
      </div>
      {error && <p className="text-red-600 text-sm mt-2">{error}</p>}

      {open && clientSecret && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={closeModal}
        >
          <div
            className="bg-[rgb(var(--color-background))] rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center mb-4">
              <h4 className="font-semibold">Complete sponsorship payment</h4>
              <button
                type="button"
                onClick={closeModal}
                className="text-[rgb(var(--color-text-secondary))] hover:text-[rgb(var(--color-text))]"
              >
                ×
              </button>
            </div>
            <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-4">
              {currency} {amount.toFixed(2)} for sponsorship
            </p>
            <Elements
              stripe={stripePromise}
              options={{
                clientSecret,
                appearance: { theme: "stripe" },
              }}
            >
              <SponsorshipPaymentForm
                amount={amount}
                currency={currency}
                onSuccess={closeModal}
                onError={setError}
              />
            </Elements>
          </div>
        </div>
      )}
    </section>
  );
}
