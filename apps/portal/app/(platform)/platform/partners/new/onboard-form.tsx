"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export function OnboardPartnerForm() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const form = e.currentTarget;
    const formData = new FormData(form);

    try {
      const res = await fetch("/api/platform/partners", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_name: formData.get("businessName"),
          contact_email: formData.get("contactEmail"),
          business_type: formData.get("businessType") || undefined,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.message || "Failed to create partner");
      }

      router.push("/platform/partners");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="max-w-md space-y-4">
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
        <label htmlFor="contactEmail" className="block text-sm font-medium mb-1">
          Contact Email *
        </label>
        <input
          id="contactEmail"
          name="contactEmail"
          type="email"
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
          className="w-full px-3 py-2 rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))]"
        />
      </div>
      {error && <p className="text-sm text-[rgb(var(--color-error))]">{error}</p>}
      <Button type="submit" disabled={loading}>
        {loading ? "Creating..." : "Create Partner"}
      </Button>
    </form>
  );
}
