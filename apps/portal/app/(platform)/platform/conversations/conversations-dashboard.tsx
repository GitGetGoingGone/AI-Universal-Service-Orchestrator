"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type ConvRow = {
  id: string;
  user_id: string | null;
  anonymous_id: string | null;
  title: string | null;
  created_at: string;
  updated_at: string;
  metrics_turns: number;
  estimated_tokens_total: number | null;
  memory_health_last: string | null;
  conversation_metrics: unknown;
};

type Rollup = {
  user_key: string;
  thread_count: number;
  estimated_tokens_total: number;
};

export function ConversationsDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConvRow[]>([]);
  const [rollups, setRollups] = useState<Rollup[]>([]);
  const [userId, setUserId] = useState("");
  const [anonymousId, setAnonymousId] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const q = new URLSearchParams();
      if (userId.trim()) q.set("user_id", userId.trim());
      if (anonymousId.trim()) q.set("anonymous_id", anonymousId.trim());
      if (from.trim()) q.set("from", from.trim());
      if (to.trim()) q.set("to", to.trim());
      const res = await fetch(`/api/platform/conversations?${q.toString()}`);
      const data = await res.json();
      if (!res.ok) throw new Error(String(data.detail ?? "Failed"));
      setConversations(data.conversations ?? []);
      setRollups(data.user_rollups ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }, [userId, anonymousId, from, to]);

  useEffect(() => {
    fetchData();
    // Initial load only; use "Apply filters" after editing fields.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional mount-only
  }, []);

  return (
    <div className="space-y-8 max-w-6xl">
      <section className="rounded-xl border border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface))] p-4">
        <h2 className="text-sm font-semibold text-[rgb(var(--color-text))] mb-3">Filters</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label htmlFor="f-user" className="text-xs text-[rgb(var(--color-text-secondary))]">
              User ID (UUID)
            </label>
            <input
              id="f-user"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="mt-1 w-full rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-2 py-1.5 text-sm"
            />
          </div>
          <div>
            <label htmlFor="f-anon" className="text-xs text-[rgb(var(--color-text-secondary))]">
              Anonymous ID
            </label>
            <input
              id="f-anon"
              value={anonymousId}
              onChange={(e) => setAnonymousId(e.target.value)}
              className="mt-1 w-full rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-2 py-1.5 text-sm"
            />
          </div>
          <div>
            <label htmlFor="f-from" className="text-xs text-[rgb(var(--color-text-secondary))]">
              Updated from (ISO)
            </label>
            <input
              id="f-from"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              placeholder="2025-01-01T00:00:00Z"
              className="mt-1 w-full rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-2 py-1.5 text-sm font-mono text-xs"
            />
          </div>
          <div>
            <label htmlFor="f-to" className="text-xs text-[rgb(var(--color-text-secondary))]">
              Updated to (ISO)
            </label>
            <input
              id="f-to"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="mt-1 w-full rounded-md border border-[rgb(var(--color-border))] bg-[rgb(var(--color-background))] px-2 py-1.5 text-sm font-mono text-xs"
            />
          </div>
        </div>
        <Button type="button" className="mt-3" onClick={fetchData} disabled={loading}>
          {loading ? "Loading…" : "Apply filters"}
        </Button>
      </section>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <section>
        <h2 className="text-lg font-semibold text-[rgb(var(--color-text))] mb-3">Per-user rollups</h2>
        <div className="overflow-x-auto rounded-xl border border-[rgb(var(--color-border))]">
          <table className="w-full text-sm">
            <thead className="bg-[rgb(var(--color-border))]/30 text-left">
              <tr>
                <th className="p-2 font-medium">User / anon key</th>
                <th className="p-2 font-medium">Threads</th>
                <th className="p-2 font-medium">Est. tokens (sum)</th>
              </tr>
            </thead>
            <tbody>
              {rollups.map((r) => (
                <tr key={r.user_key} className="border-t border-[rgb(var(--color-border))]">
                  <td className="p-2 font-mono text-xs break-all">{r.user_key}</td>
                  <td className="p-2">{r.thread_count}</td>
                  <td className="p-2">{r.estimated_tokens_total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-[rgb(var(--color-text))] mb-3">Conversations</h2>
        <div className="overflow-x-auto rounded-xl border border-[rgb(var(--color-border))]">
          <table className="w-full text-sm">
            <thead className="bg-[rgb(var(--color-border))]/30 text-left">
              <tr>
                <th className="p-2 font-medium">Thread</th>
                <th className="p-2 font-medium">Title</th>
                <th className="p-2 font-medium">User</th>
                <th className="p-2 font-medium">Updated</th>
                <th className="p-2 font-medium">Metric turns</th>
                <th className="p-2 font-medium">Tokens (est.)</th>
                <th className="p-2 font-medium">Memory</th>
              </tr>
            </thead>
            <tbody>
              {conversations.map((c) => (
                <Fragment key={c.id}>
                  <tr className="border-t border-[rgb(var(--color-border))]">
                    <td className="p-2 font-mono text-xs">
                      <button
                        type="button"
                        className="text-left underline text-[rgb(var(--color-primary))]"
                        onClick={() => setExpanded((x) => (x === c.id ? null : c.id))}
                        aria-expanded={expanded === c.id}
                      >
                        {c.id.slice(0, 8)}…
                      </button>
                    </td>
                    <td className="p-2 max-w-[180px] truncate">{c.title ?? "—"}</td>
                    <td className="p-2 font-mono text-[10px] break-all max-w-[120px]">
                      {c.user_id ?? c.anonymous_id ?? "—"}
                    </td>
                    <td className="p-2 whitespace-nowrap text-xs">{new Date(c.updated_at).toLocaleString()}</td>
                    <td className="p-2">{c.metrics_turns}</td>
                    <td className="p-2">{c.estimated_tokens_total ?? "—"}</td>
                    <td className="p-2 text-xs">{c.memory_health_last ?? "—"}</td>
                  </tr>
                  {expanded === c.id && (
                    <tr className="bg-[rgb(var(--color-background))]">
                      <td colSpan={7} className="p-3">
                        <pre className="text-xs overflow-x-auto max-h-64 overflow-y-auto font-mono whitespace-pre-wrap break-all">
                          {JSON.stringify(c.conversation_metrics, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
