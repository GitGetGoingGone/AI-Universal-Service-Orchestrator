import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { OrderQueue } from "./order-queue";

export default async function OrdersPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Order Queue</h1>
      <OrderQueue />
    </main>
  );
}
