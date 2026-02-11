"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { PartnerGuard, PartnerRequiredMessage } from "@/components/partner-guard";

type Task = {
  id: string;
  order_id: string;
  order_leg_id: string;
  partner_id: string;
  task_sequence: number;
  task_type: string;
  status: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export function TasksList() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actioning, setActioning] = useState<string | null>(null);

  async function fetchTasks() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/tasks?status=pending");
      if (res.status === 403) {
        setError("PARTNER_REQUIRED");
        return;
      }
      if (res.status === 503) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Task queue not configured");
        return;
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to load");
      }
      const data = await res.json();
      setTasks(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchTasks();
  }, []);

  async function startTask(id: string) {
    setActioning(id);
    try {
      const res = await fetch(`/api/tasks/${id}/start`, { method: "POST" });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed");
      }
      fetchTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start");
    } finally {
      setActioning(null);
    }
  }

  async function completeTask(id: string) {
    setActioning(id);
    try {
      const res = await fetch(`/api/tasks/${id}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ metadata: { notes: "Completed via portal" } }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed");
      }
      fetchTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete");
    } finally {
      setActioning(null);
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (error === "PARTNER_REQUIRED") return <PartnerRequiredMessage />;
  if (error) return <p className="text-[rgb(var(--color-error))]">{error}</p>;

  if (tasks.length === 0) {
    return (
      <div className="rounded-lg border border-[rgb(var(--color-border))] p-6 text-center text-[rgb(var(--color-text-secondary))]">
        No pending tasks. Tasks appear when orders include your products and prior tasks in the sequence
        are complete.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {tasks.map((task) => (
        <div
          key={task.id}
          className="rounded-lg border border-[rgb(var(--color-border))] p-4 bg-[rgb(var(--color-surface))]"
        >
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-medium">
                Task #{task.task_sequence} – {task.task_type}
              </p>
              <p className="text-sm text-[rgb(var(--color-text-secondary))]">
                Order: {task.order_id} • Status: {task.status}
              </p>
            </div>
            <div className="flex gap-2">
              {task.status === "pending" && (
                <Button
                  size="sm"
                  onClick={() => startTask(task.id)}
                  disabled={!!actioning}
                >
                  {actioning === task.id ? "Starting…" : "Start"}
                </Button>
              )}
              {task.status === "in_progress" && (
                <Button
                  size="sm"
                  onClick={() => completeTask(task.id)}
                  disabled={!!actioning}
                >
                  {actioning === task.id ? "Completing…" : "Complete"}
                </Button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
