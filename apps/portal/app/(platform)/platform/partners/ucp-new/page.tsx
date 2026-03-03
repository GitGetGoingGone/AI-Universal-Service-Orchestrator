import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { AddUCPPartnerForm } from "./add-ucp-partner-form";

export default async function AddUCPPartnerPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Add UCP Partner</h1>
      <p className="text-[rgb(var(--color-text-secondary))] text-sm mb-6">
        Add a store that exposes UCP (e.g. /.well-known/ucp.json). Paste the manifest JSON to auto-fill base URL, or enter base URL and display name manually.
      </p>
      <AddUCPPartnerForm />
    </main>
  );
}
