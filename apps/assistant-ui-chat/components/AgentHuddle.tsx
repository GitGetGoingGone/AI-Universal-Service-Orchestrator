"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  readMaCancelNextQueue,
  queueMaCancelNext,
  unqueueMaCancelNext,
  takeMaCancelNextForSend,
  MA_CANCEL_QUEUE_CHANGED_EVENT,
} from "@/lib/ma-cancel-queue";
import {
  AlertCircle,
  Brain,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Cpu,
  Lightbulb,
  Loader2,
  MinusCircle,
  Terminal,
} from "lucide-react";

type AgentOp = {
  phase?: "PLAN" | "ACTION" | "OBSERVE";
  label?: string;
  detail?: string;
  timestamp?: number;
};

export type AgentRow = {
  id?: string;
  label?: string;
  status?: string;
  summary?: string;
  operations?: { label?: string; status?: string }[];
  user_cancellable?: boolean;
  trace?: AgentOp[];
};

export type TodoItem = { label?: string; status?: "pending" | "in_progress" | "done" };

export type ThoughtLine = { label?: string; duration_ms?: number; detail?: string };

function notifyCancelQueueChanged() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(MA_CANCEL_QUEUE_CHANGED_EVENT));
  }
}

export function queueSkipAgentForNextTurn(agentId: string) {
  queueMaCancelNext(agentId);
  notifyCancelQueueChanged();
}

export function unqueueSkipAgentForNextTurn(agentId: string) {
  unqueueMaCancelNext(agentId);
  notifyCancelQueueChanged();
}

/** @deprecated Prefer takeMaCancelNextForSend from @/lib/ma-cancel-queue */
export function takeCancelAgentIdsForRequest(): string[] {
  return takeMaCancelNextForSend();
}

export function readQueuedSkipAgentIds(): string[] {
  return readMaCancelNextQueue();
}

function StatusIcon({ status }: { status?: string }) {
  const s = (status || "").toLowerCase();
  if (s === "running" || s === "pending")
    return <Loader2 className="h-4 w-4 animate-spin text-[var(--primary,#2563eb)]" aria-hidden />;
  if (s === "succeeded") return <Check className="h-4 w-4 text-emerald-600" aria-hidden />;
  if (s === "failed") return <AlertCircle className="h-4 w-4 text-amber-600" aria-hidden />;
  if (s === "cancelled") return <MinusCircle className="h-4 w-4 text-slate-400" aria-hidden />;
  return <Cpu className="h-4 w-4 text-slate-500" aria-hidden />;
}

function TraceLine({ op }: { op: AgentOp }) {
  const phase = op.phase || "PLAN";
  if (phase === "PLAN") {
    return (
      <li className="flex gap-2 text-sm italic text-[var(--foreground)]/90">
        <Brain className="mt-0.5 h-4 w-4 shrink-0 text-violet-500" aria-hidden />
        <span>{op.label}</span>
      </li>
    );
  }
  if (phase === "ACTION") {
    return (
      <li className="flex gap-2 font-mono text-xs text-[var(--foreground)]">
        <Terminal className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" aria-hidden />
        <span>{op.label}</span>
      </li>
    );
  }
  return (
    <li className="flex gap-2 text-sm font-semibold text-[var(--foreground)]">
      <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" aria-hidden />
      <span>{op.label}</span>
    </li>
  );
}

export function AgentHuddle({
  multi_agent_status,
  todos,
  thought_timelines,
  memory_health,
  credit_usage,
  /** When true, the huddle card starts collapsed (e.g. past turns in the thread). */
  defaultCollapsed = false,
}: {
  multi_agent_status?: { agents?: AgentRow[] };
  todos?: TodoItem[];
  thought_timelines?: ThoughtLine[];
  memory_health?: { label?: string; status?: string; detail?: string };
  credit_usage?: { estimated_total_tokens?: number; note?: string };
  defaultCollapsed?: boolean;
}) {
  const agents = multi_agent_status?.agents ?? [];
  const [huddleOpen, setHuddleOpen] = useState(() => !defaultCollapsed);
  useEffect(() => {
    setHuddleOpen(!defaultCollapsed);
  }, [defaultCollapsed]);
  const [openTrace, setOpenTrace] = useState<Record<string, boolean>>({});
  const [queuedSkipIds, setQueuedSkipIds] = useState<Set<string>>(() => new Set(readMaCancelNextQueue()));

  const syncQueuedFromStorage = useCallback(() => {
    setQueuedSkipIds(new Set(readMaCancelNextQueue()));
  }, []);

  useEffect(() => {
    syncQueuedFromStorage();
  }, [agents, syncQueuedFromStorage]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onChange = () => syncQueuedFromStorage();
    window.addEventListener(MA_CANCEL_QUEUE_CHANGED_EVENT, onChange);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener(MA_CANCEL_QUEUE_CHANGED_EVENT, onChange);
      window.removeEventListener("storage", onChange);
    };
  }, [syncQueuedFromStorage]);

  const toggleTrace = useCallback((id: string) => {
    setOpenTrace((o) => ({ ...o, [id]: !o[id] }));
  }, []);

  const toggleSkipNextForAgent = useCallback((agentKey: string) => {
    if (readMaCancelNextQueue().includes(agentKey)) {
      unqueueSkipAgentForNextTurn(agentKey);
    } else {
      queueSkipAgentForNextTurn(agentKey);
    }
    setQueuedSkipIds(new Set(readMaCancelNextQueue()));
  }, []);

  const todoProgress = useMemo(() => {
    if (!todos?.length) return null;
    const done = todos.filter((t) => t.status === "done").length;
    return { done, total: todos.length };
  }, [todos]);

  const anyScoutRunning = useMemo(() => {
    if (agents.length === 0) return false;
    return agents.some((a) => {
      const s = (a.status || "").toLowerCase();
      return s === "running" || s === "pending";
    });
  }, [agents]);

  const [thoughtTimelinesOpen, setThoughtTimelinesOpen] = useState(true);
  useEffect(() => {
    if (anyScoutRunning) setThoughtTimelinesOpen(true);
  }, [anyScoutRunning]);
  useEffect(() => {
    if (!anyScoutRunning && agents.length > 0) setThoughtTimelinesOpen(false);
  }, [anyScoutRunning, agents.length]);

  if (agents.length === 0 && !todoProgress && !thought_timelines?.length && !memory_health && !credit_usage) {
    return null;
  }

  return (
    <details
      className="agent-huddle-root assistant-themed-surface group my-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-[var(--card-foreground)] shadow-sm dark:border-gray-700 dark:bg-gray-900/40"
      aria-label="Agent huddle — scout progress"
      open={huddleOpen}
      onToggle={(e) => setHuddleOpen(e.currentTarget.open)}
    >
      <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2 group-open:mb-3">
          <div className="flex items-center gap-2 text-sm font-medium text-[var(--foreground)]">
            <ChevronRight
              className="h-4 w-4 shrink-0 text-[var(--foreground)]/60 transition-transform group-open:rotate-90"
              aria-hidden
            />
            {anyScoutRunning ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin text-[var(--primary,#2563eb)]" aria-hidden />
                <span>Working with your concierge team</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" aria-hidden />
                <span>Scouts finished for this turn</span>
              </>
            )}
          </div>
          {credit_usage?.estimated_total_tokens != null && (
            <span className="text-xs text-[var(--foreground)]/70" title={credit_usage.note}>
              ~{credit_usage.estimated_total_tokens} tokens (est.)
            </span>
          )}
        </div>
      </summary>

      {memory_health && (
        <div className="mb-3 rounded-lg bg-[var(--muted)]/40 px-3 py-2 text-sm">
          <span className="font-medium text-[var(--foreground)]">Memory: </span>
          <span className="text-[var(--foreground)]/90">{memory_health.label}</span>
          {memory_health.detail ? (
            <p className="mt-1 text-xs text-[var(--foreground)]/70">{memory_health.detail}</p>
          ) : null}
        </div>
      )}

      {thought_timelines && thought_timelines.length > 0 && (
        <details
          className="mb-3 rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 px-3 py-2"
          open={thoughtTimelinesOpen}
          onToggle={(e) => setThoughtTimelinesOpen(e.currentTarget.open)}
        >
          <summary className="cursor-pointer text-sm font-medium text-[var(--foreground)]">
            Thought timelines
          </summary>
          <ul className="mt-2 space-y-2 text-sm text-[var(--foreground)]/85">
            {thought_timelines.map((th, i) => (
              <li key={i}>
                <span className="font-medium">{th.label}</span>
                {th.duration_ms != null && (
                  <span className="ml-2 text-xs text-[var(--foreground)]/60">
                    {th.duration_ms >= 1000
                      ? `${(th.duration_ms / 1000).toFixed(1)}s`
                      : `${th.duration_ms}ms`}
                  </span>
                )}
                {th.detail ? <p className="text-xs text-[var(--foreground)]/65">{th.detail}</p> : null}
              </li>
            ))}
          </ul>
        </details>
      )}

      {todoProgress && (
        <div className="mb-3 text-sm text-[var(--foreground)]">
          <span className="font-medium">To-dos: </span>
          <span>
            {todoProgress.done} of {todoProgress.total} complete
          </span>
          <ul className="mt-2 space-y-1">
            {(todos ?? []).map((t, i) => (
              <li key={i} className="flex items-center gap-2 text-xs text-[var(--foreground)]/80">
                {t.status === "done" ? (
                  <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden />
                ) : t.status === "in_progress" ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--primary,#2563eb)]" aria-hidden />
                ) : (
                  <span className="inline-block h-3.5 w-3.5 rounded-full border border-[var(--border)]" aria-hidden />
                )}
                {t.label}
              </li>
            ))}
          </ul>
        </div>
      )}

      <ul className="space-y-3">
        {agents.map((a) => {
          const id = a.id ?? a.label ?? "agent";
          const running = (a.status || "").toLowerCase() === "running";
          const expanded = openTrace[id] ?? running;
          const trace = a.trace ?? [];
          return (
            <li
              key={id}
              className="rounded-lg border border-[var(--border)] bg-[var(--background)]/50 p-3 dark:bg-gray-800/30"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex items-start gap-2 min-w-0">
                  <StatusIcon status={a.status} />
                  <div className="min-w-0">
                    <div className="font-medium text-[var(--foreground)]">{a.label ?? id}</div>
                    <p className="text-sm text-[var(--foreground)]/75">{a.summary}</p>
                  </div>
                </div>
                {a.user_cancellable && (
                  <button
                    type="button"
                    role="switch"
                    aria-checked={queuedSkipIds.has(id)}
                    className={
                      queuedSkipIds.has(id)
                        ? "shrink-0 rounded-md border-2 border-[var(--primary)] bg-[var(--primary)]/10 px-2 py-1 text-xs font-semibold text-[var(--foreground)] shadow-sm"
                        : "shrink-0 rounded-md border border-[var(--border)] px-2 py-1 text-xs font-medium text-[var(--foreground)] hover:bg-[var(--muted)]/50"
                    }
                    aria-label={
                      queuedSkipIds.has(id)
                        ? `${a.label ?? id} will be skipped on your next message; click to undo`
                        : `Skip ${a.label ?? id} on your next message`
                    }
                    onClick={() => toggleSkipNextForAgent(id)}
                  >
                    {queuedSkipIds.has(id) ? "Skipping next turn" : "Skip next turn"}
                  </button>
                )}
              </div>
              {trace.length > 0 && (
                <div className="mt-2">
                  <button
                    type="button"
                    className="flex items-center gap-1 text-xs font-medium text-[var(--primary,#2563eb)]"
                    aria-expanded={expanded}
                    onClick={() => toggleTrace(id)}
                  >
                    {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    Reasoning trace
                  </button>
                  {expanded && (
                    <ul className="mt-2 space-y-1.5 border-l-2 border-[var(--border)] pl-3" role="list">
                      {trace.map((op, j) => (
                        <TraceLine key={j} op={op} />
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </details>
  );
}
