"use client";

import { useState } from "react";
import { useAuthState } from "./AuthWrapper";

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

  if (!hasClerk || !isSignedIn) return null;

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
            return d.startsWith("+") ? phone.trim() : `+${d}`;
          })(),
        }),
      });
      const data = await res.json();
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

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-sm px-3 py-1.5 rounded-lg border border-[var(--border)] hover:bg-[var(--card)]"
      >
        Connect WhatsApp
      </button>
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="max-w-sm w-full rounded-xl bg-[var(--card)] p-6 border border-[var(--border)]"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold mb-2">Connect WhatsApp</h3>
            <p className="text-sm text-[var(--muted)] mb-4">
              Enter your WhatsApp number to continue conversations from WhatsApp.
            </p>
            <form onSubmit={handleSubmit} className="space-y-4">
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 10))}
                placeholder="(555) 123-4567"
                className="w-full px-4 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)]"
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
                  className="flex-1 px-4 py-2 rounded-lg border border-[var(--border)]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || phone.replace(/\D/g, "").length < 10}
                  className="flex-1 px-4 py-2 rounded-lg bg-[var(--primary-color)] text-[var(--primary-foreground)] disabled:opacity-50"
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
