import { auth } from "@clerk/nextjs/server";
import Link from "next/link";
import { redirect } from "next/navigation";
import { ShopifyPartnersList } from "./shopify-partners-list";
import { Button } from "@/components/ui/button";

export default async function ShopifyPartnersPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Shopify Partners</h1>
        <Button asChild size="sm">
          <Link href="/platform/partners/shopify-new">Add Shopify partner</Link>
        </Button>
      </div>
      <p className="text-[rgb(var(--color-text-secondary))] text-sm mb-6">
        Curated Shopify stores (MCP) used in discovery. Edit premium, display name, and MCP endpoint here.
      </p>
      <p className="text-xs text-[rgb(var(--color-text-secondary))] mb-4 rounded bg-[rgb(var(--color-muted))] p-3">
        <strong>MCP contract:</strong> The store&apos;s MCP endpoint must accept JSON-RPC <code className="bg-black/10 px-1 rounded">tools/call</code> with
        method <code className="bg-black/10 px-1 rounded">search_shop_catalog</code> and return products in the response (e.g. <code className="bg-black/10 px-1 rounded">result.content[].text</code> as JSON, or <code className="bg-black/10 px-1 rounded">result.products</code>). If discovery says &quot;we don&apos;t have X&quot;, check Discovery logs for &quot;Shopify MCP&quot; (timeout, non-JSON, or no products extracted).
      </p>
      <ShopifyPartnersList />
    </main>
  );
}
