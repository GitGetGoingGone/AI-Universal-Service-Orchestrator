"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTheme } from "@/components/ThemeProvider";
import { ConnectWhatsApp } from "@/components/ConnectWhatsApp";
import { AuthButtons } from "@/components/AuthWrapper";
import type { ThemeId } from "@/lib/theme";

const THEME_OPTIONS: { id: ThemeId; label: string }[] = [
  { id: "spring", label: "Spring" },
  { id: "summer", label: "Summer" },
  { id: "autumn", label: "Autumn" },
  { id: "winter", label: "Winter" },
];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--background)]">
        <p className="text-[var(--muted)]">Loading…</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-[var(--background)]">
      <header className="flex h-14 shrink-0 items-center border-b border-[var(--border)] bg-[var(--background)] px-4">
        <Link href="/" className="text-sm font-semibold text-[var(--foreground)] hover:underline">
          ← Back to chat
        </Link>
      </header>
      <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-8">
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Settings</h1>

        <section className="mt-8">
          <h2 className="text-sm font-medium uppercase tracking-wider text-[var(--muted)]">
            Account
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Sign in to sync conversations and connect WhatsApp.
          </p>
          <div className="mt-3">
            <AuthButtons />
          </div>
        </section>

        <section className="mt-8">
          <h2 className="text-sm font-medium uppercase tracking-wider text-[var(--muted)]">
            Connect WhatsApp
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Link your WhatsApp number to continue conversations from WhatsApp and get order updates.
          </p>
          <div className="mt-3">
            <ConnectWhatsApp />
          </div>
        </section>

        <section className="mt-8">
          <h2 className="text-sm font-medium uppercase tracking-wider text-[var(--muted)]">
            Theme
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Choose a theme for the chat interface.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {THEME_OPTIONS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => setTheme(id)}
                className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                  theme === id
                    ? "border-[var(--primary)] bg-[var(--primary)] text-[var(--primary-foreground)]"
                    : "border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] hover:bg-[var(--card)]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
