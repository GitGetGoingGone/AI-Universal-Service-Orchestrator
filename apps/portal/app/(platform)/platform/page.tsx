import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { PlatformDashboard } from "./platform-dashboard";

export default async function PlatformDashboardPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Platform Dashboard</h1>
      <PlatformDashboard />
    </main>
  );
}
