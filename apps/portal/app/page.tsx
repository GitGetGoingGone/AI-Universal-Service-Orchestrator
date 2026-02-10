import Link from "next/link";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ThemeSwitcher } from "@/components/theme-switcher";

export default async function HomePage() {
  const { userId } = await auth();

  if (userId) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen bg-[rgb(var(--color-background))] text-[rgb(var(--color-text))]">
      <header className="border-b border-[rgb(var(--color-border))] px-6 py-4 flex justify-between items-center">
        <h1 className="text-xl font-semibold">USO</h1>
        <ThemeSwitcher />
      </header>

      <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-16">
        <section className="text-center space-y-8">
          <h2 className="text-4xl font-bold">
            Universal Service Orchestrator
          </h2>
          <p className="text-lg text-[rgb(var(--color-text-secondary))] max-w-2xl mx-auto">
            Connect your business to AI-powered discovery. Manage products,
            orders, and earnings in one place.
          </p>

          <div className="flex gap-4 justify-center flex-wrap">
            <Button asChild size="lg">
              <Link href="/register">Register as Partner</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/sign-in">Sign in</Link>
            </Button>
          </div>
          <p className="text-sm text-[rgb(var(--color-text-secondary))]">
            Platform admin?{" "}
            <Link href="/platform/login" className="text-[rgb(var(--color-primary))] hover:underline">
              Sign in to Platform Portal
            </Link>
          </p>
        </section>

        <section className="mt-24 grid md:grid-cols-3 gap-8">
          <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
            <h3 className="font-semibold text-lg mb-2">Discovery</h3>
            <p className="text-[rgb(var(--color-text-secondary))]">
              Get discovered by customers via ChatGPT, Gemini, and more.
            </p>
          </div>
          <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
            <h3 className="font-semibold text-lg mb-2">Order Management</h3>
            <p className="text-[rgb(var(--color-text-secondary))]">
              Accept, manage, and fulfill orders from a unified queue.
            </p>
          </div>
          <div className="p-6 rounded-lg bg-[rgb(var(--color-surface))] border border-[rgb(var(--color-border))]">
            <h3 className="font-semibold text-lg mb-2">Analytics</h3>
            <p className="text-[rgb(var(--color-text-secondary))]">
              Track sales, earnings, and insights to grow your business.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
