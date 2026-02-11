import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { RfpsList } from "./rfps-list";

export default async function RfpsPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Hub RFPs</h1>
      <p className="text-[rgb(var(--color-text-secondary))] mb-6">
        View open assembly/delivery requests and submit bids. Add capacity to appear in capacity
        matching.
      </p>
      <RfpsList />
    </main>
  );
}
