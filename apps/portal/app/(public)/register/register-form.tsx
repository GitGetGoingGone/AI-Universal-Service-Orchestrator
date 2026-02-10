"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";

type RegisterFormProps = {
  userEmail?: string | null;
};

export function RegisterForm({ userEmail }: RegisterFormProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const form = e.currentTarget;
    const formData = new FormData(form);
    const businessName = formData.get("businessName") as string;
    const businessType = formData.get("businessType") as string;

    try {
      const res = await fetch("/api/partners/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_name: businessName,
          business_type: businessType || undefined,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.message || "Registration failed");
      }

      router.push("/register/success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {userEmail && (
        <div className="rounded-lg border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] px-4 py-2 text-sm">
          <span className="text-[rgb(var(--color-text-secondary))]">Account email: </span>
          <span className="font-medium">{userEmail}</span>
          <p className="mt-1 text-xs text-[rgb(var(--color-text-secondary))]">
            You will sign in with this email after approval.
          </p>
        </div>
      )}

      <div>
        <label htmlFor="businessName" className="block text-sm font-medium mb-1">
          Business Name *
        </label>
        <input
          id="businessName"
          name="businessName"
          type="text"
          required
          className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        />
      </div>

      <div>
        <label htmlFor="businessType" className="block text-sm font-medium mb-1">
          Business Type
        </label>
        <input
          id="businessType"
          name="businessType"
          type="text"
          placeholder="e.g. restaurant, salon, delivery"
          className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        />
      </div>

      {error && (
        <p className="text-sm text-[rgb(var(--color-error))]">{error}</p>
      )}

      <Button type="submit" disabled={loading} className="w-full">
        {loading ? "Submitting..." : "Submit Application"}
      </Button>
    </form>
  );
}
