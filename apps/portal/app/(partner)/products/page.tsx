import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { ProductsList } from "./products-list";

export default async function ProductsPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-6">Products</h1>
        <ProductsList />
    </main>
  );
}
