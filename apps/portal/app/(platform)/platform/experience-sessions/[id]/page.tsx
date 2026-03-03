import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { ExperienceSessionDetail } from "./experience-session-detail";

export default async function ExperienceSessionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { userId } = await auth();
  if (!userId) redirect("/platform/login");
  const { id } = await params;

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <ExperienceSessionDetail sessionId={id} />
    </main>
  );
}
