"use client";

import Link from "next/link";
import { useTheme } from "@/components/ThemeProvider";
import { AuthButtons } from "@/components/AuthWrapper";
import { SideNav } from "@/components/SideNav";
import type { ThemeId } from "@/lib/theme";

const THEME_OPTIONS: { id: ThemeId; label: string }[] = [
  { id: "spring", label: "Spring" },
  { id: "summer", label: "Summer" },
  { id: "autumn", label: "Autumn" },
  { id: "winter", label: "Winter" },
];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex h-screen bg-[var(--background)]">
      <SideNav />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex flex-shrink-0 items-center justify-end border-b border-[var(--border)] px-4 py-3">
          <AuthButtons />
        </header>
        <div className="flex-1 overflow-y-auto p-8">
        <div className="mx-auto max-w-2xl">
          <h1 className="text-2xl font-bold text-[var(--foreground)]">Settings</h1>

        {/* Theme */}
        <section className="mt-8">
          <h2 className="text-sm font-medium text-[var(--muted)] uppercase tracking-wider">
            Theme
          </h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {THEME_OPTIONS.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => setTheme(id)}
                className={`rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                  theme === id
                    ? "border-[var(--primary-color)] bg-[var(--primary-color)]/20 text-[var(--primary-color)]"
                    : "border-[var(--border)] bg-[var(--card)] text-[var(--card-foreground)] hover:border-[var(--primary-color)]/50"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </section>

        {/* Sign in */}
        <section className="mt-8">
          <h2 className="text-sm font-medium text-[var(--muted)] uppercase tracking-wider">
            Account
          </h2>
          <div className="mt-3">
            <AuthButtons />
          </div>
        </section>

          <Link
            href="/"
            className="mt-8 inline-block text-sm text-[var(--primary-color)] hover:underline"
          >
            ← Back to chat
          </Link>
        </div>
        </div>
      </div>
    </div>
  );
}
