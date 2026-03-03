"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Session = {
  id: string;
  thread_id: string;
  user_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export function ExperienceSessionsList() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [threadFilter, setThreadFilter] = useState("");

  async function fetchSessions() {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "50" });
      if (threadFilter.trim()) params.set("thread_id", threadFilter.trim());
      const res = await fetch(`/api/platform/experience-sessions?${params}`);
      if (!res.ok) throw new Error("Failed to load sessions");
      const data = await res.json();
      setSessions(data.sessions ?? []);
    } catch {
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSessions();
  }, []);

  if (loading) {
    return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2 items-center">
        <input
          type="text"
          placeholder="Filter by thread_id"
          value={threadFilter}
          onChange={(e) => setThreadFilter(e.target.value)}
          className="rounded border border-[rgb(var(--color-border))] px-3 py-2 text-sm bg-[rgb(var(--color-background))]"
        />
        <button
          onClick={fetchSessions}
          className="rounded bg-[rgb(var(--color-primary))] px-4 py-2 text-sm font-medium text-[rgb(var(--color-primary-foreground))]"
        >
          Search
        </button>
      </div>
      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-x-auto">
        <table className="w-full min-w-[700px]">
          <thead className="bg-[rgb(var(--color-surface))]">
            <tr>
              <th className="text-left px-4 py-2">Session</th>
              <th className="text-left px-4 py-2">Thread</th>
              <th className="text-left px-4 py-2">User</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Created</th>
              <th className="text-left px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id} className="border-t border-[rgb(var(--color-border))]">
                <td className="px-4 py-2 font-mono text-sm" title={s.id}>
                  {s.id.slice(0, 8)}…
                </td>
                <td className="px-4 py-2 font-mono text-xs" title={s.thread_id}>
                  {s.thread_id?.slice(0, 20)}…
                </td>
                <td className="px-4 py-2 text-sm">{s.user_id ? `${s.user_id.slice(0, 8)}…` : "—"}</td>
                <td className="px-4 py-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      s.status === "active"
                        ? "bg-green-500/20 text-green-700 dark:text-green-400"
                        : "bg-gray-500/20 text-gray-700 dark:text-gray-400"
                    }`}
                  >
                    {s.status}
                  </span>
                </td>
                <td className="px-4 py-2 text-sm text-[rgb(var(--color-text-secondary))]">
                  {s.created_at ? new Date(s.created_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-2">
                  <Link
                    href={`/platform/experience-sessions/${s.id}`}
                    className="text-[rgb(var(--color-primary))] hover:underline text-sm"
                  >
                    View legs
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {sessions.length === 0 && (
        <p className="text-[rgb(var(--color-text-secondary))]">No experience sessions found.</p>
      )}
    </div>
  );
}
