import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import { AdminsList } from "./admins-list";

export default async function AdminsPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <div className="min-h-screen bg-[rgb(var(--color-background))] text-[rgb(var(--color-text))]">
      <header className="border-b border-[rgb(var(--color-border))] px-6 py-4">
        <nav className="flex gap-4">
          <Link href="/platform">Dashboard</Link>
          <Link href="/platform/partners">Partners</Link>
          <Link href="/platform/admins" className="font-medium">Admins</Link>
          <Link href="/platform/config">Config</Link>
        </nav>
      </header>
      <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-6">Super Admins</h1>
        <AdminsList />
      </main>
    </div>
  );
}
