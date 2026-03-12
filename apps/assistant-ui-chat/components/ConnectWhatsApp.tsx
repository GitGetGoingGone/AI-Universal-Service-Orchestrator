"use client";

import { useState } from "react";
import { useAuthState } from "@/components/AuthWrapper";

const hasClerk = !!(
  typeof process !== "undefined" &&
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
);

export function ConnectWhatsApp() {
  const { isSignedIn } = useAuthState();
  const [open, setOpen] = useState(false);
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim() || loading) return;
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch("/api/link-account", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: "whatsapp",
          platform_user_id: (() => {
            const d = phone.trim().replace(/\D/g, "");
            if (d.length === 10) return `+1${d}`;
            if (d.length === 11 && d.startsWith("1")) return `+${d}`;
            return phone.trim().startsWith("+") ? phone.trim() : `+${phone.trim()}`;
          })(),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setMessage("WhatsApp linked! You can now message from WhatsApp.");
        setPhone("");
        setTimeout(() => setOpen(false), 2000);
      } else {
        setMessage(data.error || "Failed to link");
      }
    } catch {
      setMessage("Request failed");
    } finally {
      setLoading(false);
    }
  };

  if (!hasClerk) return null;

  if (!isSignedIn) {
    return (
      <p className="text-sm text-[var(--muted)]">
        Sign in to connect your WhatsApp number and continue conversations from WhatsApp.
      </p>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-sm hover:bg-[var(--card)]"
      >
        Connect WhatsApp
      </button>
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-sm rounded-xl border border-[var(--border)] bg-[var(--card)] p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-2 text-lg font-semibold text-[var(--foreground)]">Connect WhatsApp</h3>
            <p className="mb-4 text-sm text-[var(--muted)]">
              Enter your WhatsApp number to continue conversations from WhatsApp.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 11))}
                placeholder="(555) 123-4567"
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-4 py-2 text-[var(--foreground)]"
                disabled={loading}
              />
              {message && (
                <p className={`text-sm ${message.includes("linked") ? "text-green-600" : "text-red-500"}`}>
                  {message}
                </p>
              )}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="flex-1 rounded-lg border border-[var(--border)] px-4 py-2 text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || phone.replace(/\D/g, "").length < 10}
                  className="flex-1 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm text-[var(--primary-foreground)] disabled:opacity-50"
                >
                  {loading ? "Linking…" : "Link"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
