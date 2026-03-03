import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";
import { UCPPartnersList } from "./ucp-partners-list";
import { Button } from "@/components/ui/button";

export default async function UCPPartnersPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">UCP Partners</h1>
        <Button asChild size="sm">
          <Link href="/platform/partners/ucp-new">Add UCP partner</Link>
        </Button>
      </div>
      <p className="text-[rgb(var(--color-text-secondary))] text-sm mb-6">
        Stores that expose a UCP manifest (e.g. /.well-known/ucp.json). Discovery fetches the manifest from each base URL and searches the catalog.
      </p>
      <UCPPartnersList />
    </main>
  );
}
