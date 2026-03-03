import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { AddShopifyPartnerForm } from "./add-shopify-partner-form";

export default async function AddShopifyPartnerPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Add Shopify Partner</h1>
      <p className="text-[rgb(var(--color-text-secondary))] text-sm mb-6">
        Onboard a curated Shopify store (MCP). Discovery will use the MCP endpoint to search their catalog. Access token is optional and can be added later for Draft Orders.
      </p>
      <AddShopifyPartnerForm />
    </main>
  );
}
