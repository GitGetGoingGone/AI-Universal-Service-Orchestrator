import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { InventoryList } from "./inventory-list";

export default async function InventoryPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Inventory</h1>
      <InventoryList />
    </main>
  );
}
