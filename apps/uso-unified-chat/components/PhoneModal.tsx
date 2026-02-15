"use client";

import { useState } from "react";

export type PhoneModalProps = {
  orderId: string;
  onClose: () => void;
  onComplete: (orderId: string) => void;
};

export function PhoneModal({
  orderId,
  onClose,
  onComplete,
}: PhoneModalProps) {
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/orders/${orderId}/contact`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.error || "Failed to save");
        return;
      }
      onComplete(orderId);
    } catch {
      setError("Request failed");
    } finally {
      setLoading(false);
    }
  };

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
          <h2 className="text-lg font-semibold">Contact for your order</h2>
          <button
            onClick={onClose}
            className="text-[var(--muted)] hover:text-[var(--foreground)] text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <p className="text-sm text-[var(--muted)] mb-4">
          We need your phone number to contact you about this order.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="e.g. 555 123 4567"
            disabled={loading}
            className="w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 py-3 text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none focus:ring-2 focus:ring-[var(--primary-color)]"
            autoFocus
          />
          {error && (
            <p className="text-sm text-red-500">{error}</p>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 rounded-xl border border-[var(--border)] bg-[var(--card)] text-[var(--card-foreground)] font-medium hover:bg-[var(--border)]/20"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!phone.trim() || loading}
              className="flex-1 px-4 py-3 rounded-xl bg-[var(--primary-color)] text-[var(--primary-foreground)] font-medium disabled:opacity-50"
            >
              {loading ? "Saving…" : "Continue to payment"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
