import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import Link from "next/link";
import { ProductEditForm } from "./product-edit-form";
import { AvailabilityCalendar } from "./availability-calendar";

export default async function ProductDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  const { id } = await params;

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
        <Link href="/products" className="text-[rgb(var(--color-primary))] hover:underline mb-4 inline-block">
          ← Back to Products
        </Link>
        <h1 className="text-2xl font-bold mb-6">Edit Product</h1>
        <ProductEditForm productId={id} />
        <h2 className="text-lg font-semibold mt-8 mb-2">Availability</h2>
        <AvailabilityCalendar productId={id} />
    </main>
  );
}
