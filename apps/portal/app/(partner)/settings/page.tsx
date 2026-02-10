import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { ThemeSwitcher } from "@/components/theme-switcher";
import { CommerceProfileForm } from "@/components/commerce-profile-form";

export default async function SettingsPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-2">Theme</h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-3">
          Choose a color theme for the portal.
        </p>
        <ThemeSwitcher />
      </section>

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-2">Commerce profile (AI catalog)</h2>
        <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-3">
          Seller and policy URLs used for ChatGPT and Gemini discovery.
        </p>
        <CommerceProfileForm />
      </section>
    </main>
  );
}
