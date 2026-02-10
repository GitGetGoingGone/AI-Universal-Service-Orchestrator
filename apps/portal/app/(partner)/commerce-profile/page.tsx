import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { CommerceProfileForm } from "@/components/commerce-profile-form";

export default async function CommerceProfilePage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Commerce profile</h1>
      <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-6">
        Seller and policy URLs used for ChatGPT and Gemini discovery (AI catalog).
      </p>
      <CommerceProfileForm />
    </main>
  );
}
