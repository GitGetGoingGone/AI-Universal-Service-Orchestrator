"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Leg = {
  id: string;
  partner_id: string;
  product_id: string;
  status: string;
  partner_name?: string | null;
  shopify_draft_order_id?: string | null;
  created_at: string;
  updated_at: string;
};

type Session = {
  id: string;
  thread_id: string;
  user_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  legs?: Leg[];
};

const LEG_STATUSES = ["pending", "ready", "in_customization", "committed", "failed"] as const;

export function ExperienceSessionDetail({ sessionId }: { sessionId: string }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [overrideLeg, setOverrideLeg] = useState<string | null>(null);
  const [overrideStatus, setOverrideStatus] = useState("");

  async function fetchSession() {
    setLoading(true);
    try {
      const res = await fetch(`/api/platform/experience-sessions/${sessionId}`);
      if (!res.ok) throw new Error("Failed to load session");
      const data = await res.json();
      setSession(data.session ?? null);
    } catch {
      setSession(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSession();
  }, [sessionId]);

  async function handleOverride(legId: string, newStatus: string) {
    try {
      const res = await fetch(`/api/platform/experience-session-legs/${legId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) throw new Error("Override failed");
      setOverrideLeg(null);
      setOverrideStatus("");
      await fetchSession();
    } catch {
      alert("Failed to override status");
    }
  }

  if (loading) return <p className="text-[rgb(var(--color-text-secondary))]">Loading...</p>;
  if (!session) return <p className="text-[rgb(var(--color-text-secondary))]">Session not found.</p>;

  const legs = session.legs ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Experience Session</h1>
        <Link
          href="/platform/experience-sessions"
          className="text-[rgb(var(--color-primary))] hover:underline text-sm"
        >
          ← Back to list
        </Link>
      </div>
      <div className="rounded-lg border border-[rgb(var(--color-border))] p-4 space-y-2">
        <p>
          <span className="font-medium text-[rgb(var(--color-text-secondary))]">Thread:</span>{" "}
          <span className="font-mono text-sm">{session.thread_id}</span>
        </p>
        <p>
          <span className="font-medium text-[rgb(var(--color-text-secondary))]">User:</span>{" "}
          {session.user_id ? `${session.user_id.slice(0, 8)}…` : "—"}
        </p>
        <p>
          <span className="font-medium text-[rgb(var(--color-text-secondary))]">Status:</span>{" "}
          <span
            className={`px-2 py-0.5 rounded text-xs font-medium ${
              session.status === "active"
                ? "bg-green-500/20 text-green-700 dark:text-green-400"
                : "bg-gray-500/20"
            }`}
          >
            {session.status}
          </span>
        </p>
      </div>
      <h2 className="text-lg font-semibold">Legs</h2>
      <div className="border border-[rgb(var(--color-border))] rounded-lg overflow-x-auto">
        <table className="w-full min-w-[600px]">
          <thead className="bg-[rgb(var(--color-surface))]">
            <tr>
              <th className="text-left px-4 py-2">Partner</th>
              <th className="text-left px-4 py-2">Product (masked)</th>
              <th className="text-left px-4 py-2">Status</th>
              <th className="text-left px-4 py-2">Updated</th>
              <th className="text-left px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {legs.map((leg) => (
              <tr key={leg.id} className="border-t border-[rgb(var(--color-border))]">
                <td className="px-4 py-2 text-sm">{leg.partner_name ?? leg.partner_id?.slice(0, 8)}</td>
                <td className="px-4 py-2 font-mono text-xs">{leg.product_id?.slice(0, 24)}…</td>
                <td className="px-4 py-2">
                  {overrideLeg === leg.id ? (
                    <div className="flex gap-2 items-center">
                      <select
                        value={overrideStatus}
                        onChange={(e) => setOverrideStatus(e.target.value)}
                        className="rounded border px-2 py-1 text-sm"
                      >
                        {LEG_STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => overrideStatus && handleOverride(leg.id, overrideStatus)}
                        className="rounded bg-green-600 px-2 py-1 text-xs text-white"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => {
                          setOverrideLeg(null);
                          setOverrideStatus("");
                        }}
                        className="rounded border px-2 py-1 text-xs"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          leg.status === "committed"
                            ? "bg-green-500/20 text-green-700 dark:text-green-400"
                            : leg.status === "failed"
                              ? "bg-red-500/20 text-red-700 dark:text-red-400"
                              : "bg-amber-500/20 text-amber-700 dark:text-amber-400"
                        }`}
                      >
                        {leg.status}
                      </span>
                      <button
                        onClick={() => {
                          setOverrideLeg(leg.id);
                          setOverrideStatus(leg.status);
                        }}
                        className="ml-2 text-xs text-[rgb(var(--color-primary))] hover:underline"
                      >
                        Override
                      </button>
                    </>
                  )}
                </td>
                <td className="px-4 py-2 text-sm text-[rgb(var(--color-text-secondary))]">
                  {leg.updated_at ? new Date(leg.updated_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-2">
                  <button
                    onClick={() => window.confirm("Send message?") && alert("Message stub – infra to be wired")}
                    className="text-xs text-[rgb(var(--color-primary))] hover:underline mr-2"
                  >
                    Message
                  </button>
                  <button
                    onClick={() => window.confirm("Send reminder?") && alert("Reminder stub – infra to be wired")}
                    className="text-xs text-[rgb(var(--color-primary))] hover:underline"
                  >
                    Remind
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {legs.length === 0 && (
        <p className="text-[rgb(var(--color-text-secondary))]">No legs in this session.</p>
      )}
    </div>
  );
}
