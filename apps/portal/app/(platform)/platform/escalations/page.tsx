import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { EscalationsList } from "./escalations-list";

export default async function EscalationsPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Support Escalations</h1>
      <EscalationsList clerkUserId={userId} />
    </main>
  );
}
