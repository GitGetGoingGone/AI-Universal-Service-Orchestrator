import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { PromotionsList } from "./promotions-list";

export default async function PromotionsPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Promotions</h1>
      <PromotionsList />
    </main>
  );
}
