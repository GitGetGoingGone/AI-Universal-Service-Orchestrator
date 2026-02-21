import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import { OrderDetail } from "./order-detail";

export default async function OrderDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  const { id } = await params;

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <div className="mb-6 flex items-center gap-4">
        <Link
          href="/platform/orders"
          className="text-sm text-[rgb(var(--color-text-secondary))] hover:text-[rgb(var(--color-text))]"
        >
          ← Orders
        </Link>
        <h1 className="text-2xl font-bold">Order details</h1>
      </div>
      <OrderDetail orderId={id} />
    </main>
  );
}
