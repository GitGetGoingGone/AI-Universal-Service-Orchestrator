"use client";

import Link from "next/link";

export default function SettingsPage() {
  return (
    <div className="min-h-screen bg-[var(--background)] p-8">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Settings</h1>
        <p className="mt-2 text-[var(--muted)]">
          Configure your preferences here.
        </p>
        <Link
          href="/"
          className="mt-6 inline-block text-sm text-[var(--primary-color)] hover:underline"
        >
          ← Back to chat
        </Link>
      </div>
    </div>
  );
}
