import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";
import { PartnersList } from "./partners-list";
import { Button } from "@/components/ui/button";

export default async function PartnersPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Partners</h1>
        <div className="flex gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href="/platform/partners/new">New partner</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/platform/partners/shopify-new">Add Shopify partner</Link>
          </Button>
        </div>
      </div>
      <PartnersList />
    </main>
  );
}
