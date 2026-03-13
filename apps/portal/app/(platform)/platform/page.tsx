import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { PlatformDashboard } from "./platform-dashboard";

export default async function PlatformDashboardPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8" role="main">
      <h1 className="text-2xl font-bold text-[rgb(var(--color-text))] mb-2">Dashboard</h1>
      <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-8">
        Platform metrics, conversations, conversion rate, and operations at a glance.
      </p>
      <PlatformDashboard />
    </main>
  );
}
