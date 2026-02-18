import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { OnboardPartnerForm } from "./onboard-form";

export default async function NewPartnerPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Onboard Partner</h1>
      <OnboardPartnerForm />
    </main>
  );
}
