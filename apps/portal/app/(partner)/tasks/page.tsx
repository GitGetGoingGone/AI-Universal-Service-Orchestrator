import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { TasksList } from "./tasks-list";

export default async function TasksPage() {
  const { userId } = await auth();
  if (!userId) redirect("/sign-in");

  return (
    <main className="max-w-[var(--content-max-width)] mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold mb-6">Task Queue</h1>
      <p className="text-[rgb(var(--color-text-secondary))] mb-6">
        View and complete fulfillment tasks for your orders. Tasks appear in sequence—complete the
        current one before the next becomes available.
      </p>
      <TasksList />
    </main>
  );
}
