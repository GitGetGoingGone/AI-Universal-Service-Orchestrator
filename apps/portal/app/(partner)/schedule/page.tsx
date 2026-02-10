import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { ScheduleEditor } from "./schedule-editor";

export default async function SchedulePage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Business Hours</h1>
      <ScheduleEditor />
    </main>
  );
}
