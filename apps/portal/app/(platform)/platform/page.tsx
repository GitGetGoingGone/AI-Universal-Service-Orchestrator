import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import { PlatformDashboard } from "./platform-dashboard";

export default async function PlatformDashboardPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <div className="min-h-screen bg-[rgb(var(--color-background))] text-[rgb(var(--color-text))]">
      <header className="border-b border-[rgb(var(--color-border))] px-6 py-4">
        <nav className="flex gap-4">
          <Link href="/platform" className="font-medium">
            Dashboard
          </Link>
          <Link href="/platform/partners" className="text-[rgb(var(--color-text-secondary))] hover:text-[rgb(var(--color-text))]">
            Partners
          </Link>
          <Link href="/platform/admins" className="text-[rgb(var(--color-text-secondary))] hover:text-[rgb(var(--color-text))]">
            Admins
          </Link>
          <Link href="/platform/config" className="text-[rgb(var(--color-text-secondary))] hover:text-[rgb(var(--color-text))]">
            Config
          </Link>
        </nav>
      </header>

      <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-6">Platform Dashboard</h1>
        <PlatformDashboard />
      </main>
    </div>
  );
}
