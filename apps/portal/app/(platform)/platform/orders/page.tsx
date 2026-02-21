import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { OrdersList } from "./orders-list";

export default async function OrdersPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Orders</h1>
      <OrdersList />
    </main>
  );
}
