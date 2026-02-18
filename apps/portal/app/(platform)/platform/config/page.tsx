import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { ConfigEditor } from "./config-editor";

export default async function ConfigPage() {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-2">Algorithms & Config</h1>
      <p className="text-sm text-[rgb(var(--color-text-secondary))] mb-6">
        Configure LLM providers, ranking, discovery, sponsorship, and external integrations.
      </p>
      <ConfigEditor />
    </main>
  );
}
