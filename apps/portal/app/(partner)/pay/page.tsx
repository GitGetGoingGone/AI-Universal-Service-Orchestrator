"use client";

import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, PaymentElement, useStripe, useElements } from "@stripe/react-stripe-js";
import Link from "next/link";

const stripePromise = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
  ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY, { apiVersion: "2023-10-16" })
  : null;

function PaymentForm({
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;
    setLoading(true);
    try {
      const { error } = await stripe.confirmPayment({
        elements,
        confirmParams: {
          return_url: `${window.location.origin}/pay/success?order_id=${orderId}`,
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

function PayPageContent() {
  const searchParams = useSearchParams();
  const orderId = searchParams.get("order_id");
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [amount, setAmount] = useState(0);
  const [currency, setCurrency] = useState("USD");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!orderId) {
      setLoading(false);
      setError("Order ID required");
      return;
    }
    fetch("/api/payment/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_id: orderId }),
    })
      .then(res => res.json())
      .then(data => {
        if (data.client_secret) {
          setClientSecret(data.client_secret);
          setAmount(data.amount ?? 0);
          setCurrency(data.currency ?? "USD");
        } else {
          setError(data.detail || "Failed to create payment");
        }
      })
      .catch(() => setError("Request failed"))
      .finally(() => setLoading(false));
  }, [orderId]);

  if (loading) return <p className="p-6">Loading…</p>;
  if (error || !orderId) {
    return (
      <div className="p-6 max-w-md space-y-4">
        <h1 className="text-xl font-bold">Payment</h1>
        <p className="text-[rgb(var(--color-text-secondary))]">
          {error || "Add ?order_id=YOUR_ORDER_ID to the URL."}
        </p>
        <Link href="/orders" className="text-[rgb(var(--color-primary))] hover:underline">
          ← Back to orders
        </Link>
      </div>
    );
  }

  if (!stripePromise) {
    return (
      <div className="p-6 max-w-md">
        <p className="text-amber-600">
          Stripe not configured. Set NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY.
        </p>
        <Link href="/orders" className="text-[rgb(var(--color-primary))] hover:underline">
          ← Back to orders
        </Link>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-md space-y-4">
      <h1 className="text-xl font-bold">Payment</h1>
      <p className="text-sm text-[rgb(var(--color-text-secondary))]">
        Order {orderId.slice(0, 8)}... — {currency} {amount.toFixed(2)}
      </p>
      <Elements
        stripe={stripePromise}
        options={{
          clientSecret: clientSecret!,
          appearance: { theme: "stripe" },
        }}
      >
        <PaymentForm
          orderId={orderId}
          amount={amount}
          currency={currency}
          onSuccess={() => {}}
          onError={setError}
        />
      </Elements>
      {error && (
        <p className="text-red-600 text-sm">{error}</p>
      )}
      <Link href="/orders" className="block text-sm text-[rgb(var(--color-text-secondary))] hover:text-[rgb(var(--color-text))]">
        ← Back to orders
      </Link>
    </div>
  );
}

export default function PayPage() {
  return (
    <Suspense fallback={<p className="p-6">Loading…</p>}>
      <PayPageContent />
    </Suspense>
  );
}
