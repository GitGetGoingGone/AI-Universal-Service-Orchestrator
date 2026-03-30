"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  ChevronRight,
  Coins,
  Cpu,
  Lightbulb,
  ListTodo,
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
  /** Optional per-agent token estimate when backend supplies it */
  estimated_tokens?: number;
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

function formatDurationMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms}ms`;
}

function StatusIcon({ status }: { status?: string }) {
  const s = (status || "").toLowerCase();
  if (s === "running" || s === "pending")
    return <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-[var(--primary,#2563eb)]" aria-hidden />;
  if (s === "succeeded") return <Check className="h-3.5 w-3.5 shrink-0 text-emerald-600" aria-hidden />;
  if (s === "failed") return <AlertCircle className="h-3.5 w-3.5 shrink-0 text-amber-600" aria-hidden />;
  if (s === "cancelled") return <MinusCircle className="h-3.5 w-3.5 shrink-0 text-slate-400" aria-hidden />;
  return <Cpu className="h-3.5 w-3.5 shrink-0 text-slate-500" aria-hidden />;
}

function TraceLine({ op }: { op: AgentOp }) {
  const phase = op.phase || "PLAN";
  if (phase === "PLAN") {
    return (
      <li className="flex gap-2 text-xs italic text-[var(--foreground)]/90">
        <Brain className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-500" aria-hidden />
        <span>{op.label}</span>
      </li>
    );
  }
  if (phase === "ACTION") {
    return (
      <li className="flex gap-2 font-mono text-[11px] text-[var(--foreground)]/85">
        <Terminal className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" aria-hidden />
        <span>{op.label}</span>
      </li>
    );
  }
  return (
    <li className="flex gap-2 text-xs font-semibold text-[var(--foreground)]">
      <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" aria-hidden />
      <span>{op.label}</span>
    </li>
  );
}

function TokenBadge({
  n,
  title,
}: {
  n: number;
  title?: string;
}) {
  return (
    <span
      className="flex shrink-0 items-center gap-0.5 text-xs text-[var(--muted-foreground)]"
      title={title}
    >
      <Coins className="h-3 w-3 text-amber-500" aria-hidden />
      <span>~{n}</span>
    </span>
  );
}

export function AgentHuddle({
  multi_agent_status,
  todos,
  thought_timelines,
  memory_health,
  credit_usage,
  /** When true, activity rows start collapsed (e.g. past turns). */
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
  const [openTrace, setOpenTrace] = useState<Record<string, boolean>>({});
  const [queuedSkipIds, setQueuedSkipIds] = useState<Set<string>>(() => new Set(readMaCancelNextQueue()));

  const [thoughtOpen, setThoughtOpen] = useState(() => !defaultCollapsed);
  const [todosOpen, setTodosOpen] = useState(() => !defaultCollapsed);
  const [memoryOpen, setMemoryOpen] = useState(false);

  const syncQueuedFromStorage = useCallback(() => {
    setQueuedSkipIds(new Set(readMaCancelNextQueue()));
  }, []);

  useEffect(() => {
    setThoughtOpen(!defaultCollapsed);
    setTodosOpen(!defaultCollapsed);
  }, [defaultCollapsed]);

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

  const prevRunning = useRef(anyScoutRunning);
  useEffect(() => {
    if (anyScoutRunning) {
      setThoughtOpen(true);
      setTodosOpen(true);
    } else if (prevRunning.current && !anyScoutRunning) {
      setThoughtOpen(false);
      setTodosOpen(false);
    }
    prevRunning.current = anyScoutRunning;
  }, [anyScoutRunning]);

  const thoughtDurationLabel = useMemo(() => {
    if (!thought_timelines?.length) return null;
    const total = thought_timelines.reduce((acc, t) => acc + (t.duration_ms ?? 0), 0);
    if (total <= 0) return null;
    return formatDurationMs(total);
  }, [thought_timelines]);

  const activeTodo = useMemo(() => {
    return (todos ?? []).find((t) => t.status === "in_progress");
  }, [todos]);

  if (agents.length === 0 && !todoProgress && !thought_timelines?.length && !memory_health && !credit_usage) {
    return null;
  }

  const estTokens = credit_usage?.estimated_total_tokens;

  return (
    <section
      className="agent-huddle-root my-3 space-y-2 select-text"
      aria-label="Concierge activity for this turn"
    >
      {anyScoutRunning ? (
        <div className="flex items-center gap-2 rounded-md border border-[var(--border)] bg-[var(--muted)]/25 px-3 py-2 text-xs text-[var(--foreground)]">
          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-[var(--primary,#2563eb)]" aria-hidden />
          <span className="font-medium">Concierge team in progress</span>
        </div>
      ) : (
        <div className="flex items-center gap-2 px-1 text-[11px] text-[var(--muted-foreground)]">
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-600" aria-hidden />
          <span>Turn complete</span>
          {estTokens != null ? (
            <>
              <span className="text-[var(--border)]" aria-hidden>
                ·
              </span>
              <TokenBadge n={estTokens} title={credit_usage?.note} />
            </>
          ) : null}
        </div>
      )}

      {thought_timelines && thought_timelines.length > 0 && (
        <details
          className="group/th isolate rounded-md border border-[var(--border)] bg-[var(--muted)]/20 text-sm dark:bg-[var(--muted)]/10"
          open={thoughtOpen}
          onToggle={(e) => setThoughtOpen(e.currentTarget.open)}
        >
          <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 [&::-webkit-details-marker]:hidden">
            <ChevronRight className="h-3 w-3 shrink-0 text-[var(--muted-foreground)] transition-transform duration-150 group-open/th:rotate-90" />
            <span className="text-[11px] text-[var(--muted-foreground)]">
              Thought
              {thoughtDurationLabel ? (
                <span className="opacity-80"> for {thoughtDurationLabel}</span>
              ) : null}
            </span>
          </summary>
          <ul className="space-y-2 border-t border-[var(--border)]/50 px-3 py-2 text-xs text-[var(--foreground)]/90">
            {thought_timelines.map((th, i) => (
              <li key={i}>
                <span className="font-medium">{th.label}</span>
                {th.duration_ms != null && (
                  <span className="ml-2 text-[var(--muted-foreground)]">{formatDurationMs(th.duration_ms)}</span>
                )}
                {th.detail ? <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">{th.detail}</p> : null}
              </li>
            ))}
          </ul>
        </details>
      )}

      {todoProgress && (
        <details
          className="group/td isolate rounded-md border border-[var(--border)] bg-[var(--muted)]/20 dark:bg-[var(--muted)]/10"
          open={todosOpen}
          onToggle={(e) => setTodosOpen(e.currentTarget.open)}
        >
          <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 [&::-webkit-details-marker]:hidden">
            <ChevronRight className="h-3 w-3 shrink-0 text-[var(--muted-foreground)] transition-transform duration-150 group-open/td:rotate-90" />
            <ListTodo className="h-3.5 w-3.5 shrink-0 text-[var(--muted-foreground)]" aria-hidden />
            <span className="text-xs text-[var(--foreground)]">To-dos</span>
            <span className="min-w-0 flex-1 truncate text-xs text-[var(--muted-foreground)]">
              {todoProgress.done} of {todoProgress.total} complete
            </span>
          </summary>
          <div className="border-t border-[var(--border)]/50 px-3 py-2">
            <ul className="space-y-1.5">
              {(todos ?? []).map((t, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-[var(--foreground)]/85">
                  {t.status === "done" ? (
                    <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" aria-hidden />
                  ) : t.status === "in_progress" ? (
                    <Loader2 className="mt-0.5 h-3.5 w-3.5 shrink-0 animate-spin text-[var(--primary,#2563eb)]" aria-hidden />
                  ) : (
                    <span className="mt-0.5 inline-block h-3.5 w-3.5 shrink-0 rounded-full border border-[var(--border)]" aria-hidden />
                  )}
                  <span>{t.label}</span>
                </li>
              ))}
            </ul>
            {activeTodo?.label ? (
              <p className="mt-2 text-[11px] text-[var(--muted-foreground)]">
                Started to-do <span className="text-[var(--foreground)]/70">{activeTodo.label}</span>
              </p>
            ) : null}
          </div>
        </details>
      )}

      {memory_health && (
        <details
          className="group/mem isolate rounded-md border border-[var(--border)] bg-[var(--muted)]/20 dark:bg-[var(--muted)]/10"
          open={memoryOpen}
          onToggle={(e) => setMemoryOpen(e.currentTarget.open)}
        >
          <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 [&::-webkit-details-marker]:hidden">
            <ChevronRight className="h-3 w-3 shrink-0 text-[var(--muted-foreground)] transition-transform duration-150 group-open/mem:rotate-90" />
            <span className="text-xs text-[var(--foreground)]">Memory</span>
            <span className="min-w-0 flex-1 truncate text-xs text-[var(--muted-foreground)]">{memory_health.label}</span>
          </summary>
          <div className="border-t border-[var(--border)]/50 px-3 py-2 text-xs text-[var(--foreground)]/85">
            <span className="font-medium capitalize">{memory_health.status ?? "ok"}</span>
            {memory_health.detail ? <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">{memory_health.detail}</p> : null}
          </div>
        </details>
      )}

      <ul className="space-y-2">
        {agents.map((a) => {
          const id = a.id ?? a.label ?? "agent";
          const running = (a.status || "").toLowerCase() === "running" || (a.status || "").toLowerCase() === "pending";
          const trace = a.trace ?? [];
          const userToggled = openTrace[id];
          const traceExpanded = userToggled ?? (running ? true : !defaultCollapsed);

          const rowTokens = a.estimated_tokens;
          return (
            <li
              key={id}
              className="isolate rounded-md border border-[var(--border)] bg-[var(--card)]/60 text-sm shadow-sm dark:bg-[var(--card)]/20"
            >
              <div className="flex flex-wrap items-start justify-between gap-2 px-3 py-2">
                <div className="flex min-w-0 flex-1 items-start gap-2">
                  <StatusIcon status={a.status} />
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium text-[var(--foreground)]">{a.label ?? id}</div>
                    {a.summary ? (
                      <p className="mt-0.5 line-clamp-2 text-[11px] text-[var(--muted-foreground)]">{a.summary}</p>
                    ) : null}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {rowTokens != null ? <TokenBadge n={rowTokens} /> : null}
                  {a.user_cancellable && (
                    <button
                      type="button"
                      role="switch"
                      aria-checked={queuedSkipIds.has(id)}
                      className={
                        queuedSkipIds.has(id)
                          ? "rounded-md border-2 border-[var(--primary)] bg-[var(--primary)]/10 px-2 py-1 text-[10px] font-semibold text-[var(--foreground)]"
                          : "rounded-md border border-[var(--border)] px-2 py-1 text-[10px] font-medium text-[var(--foreground)] hover:bg-[var(--muted)]/50"
                      }
                      aria-label={
                        queuedSkipIds.has(id)
                          ? `${a.label ?? id} will be skipped on your next message; click to undo`
                          : `Skip ${a.label ?? id} on your next message`
                      }
                      onClick={() => toggleSkipNextForAgent(id)}
                    >
                      {queuedSkipIds.has(id) ? "Skipping next" : "Skip next"}
                    </button>
                  )}
                </div>
              </div>

              {trace.length > 0 && (
                <div className="border-t border-[var(--border)]/50 px-3 py-2">
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 text-left text-xs font-medium text-[var(--primary,#2563eb)]"
                    aria-expanded={traceExpanded}
                    onClick={() => toggleTrace(id)}
                  >
                    <ChevronRight
                      className={`h-3.5 w-3.5 shrink-0 transition-transform ${traceExpanded ? "rotate-90" : ""}`}
                      aria-hidden
                    />
                    Reasoning trace
                    {estTokens != null && !rowTokens && agents.length === 1 ? (
                      <span className="ml-auto flex items-center gap-1">
                        <TokenBadge n={estTokens} title={credit_usage?.note} />
                      </span>
                    ) : null}
                  </button>
                  {traceExpanded && (
                    <ul className="mt-2 space-y-1.5 border-l-2 border-[var(--border)] pl-3" role="list">
                      {trace.map((op, j) => (
                        <TraceLine key={j} op={op} />
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {trace.length === 0 && estTokens != null && agents.length === 1 && !anyScoutRunning ? (
                <div className="flex items-center justify-end gap-2 border-t border-[var(--border)]/50 px-3 py-1.5">
                  <TokenBadge n={estTokens} title={credit_usage?.note} />
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>

      {estTokens != null && agents.length > 1 && !anyScoutRunning ? (
        <details className="group/usage isolate rounded-md border border-dashed border-[var(--border)] bg-[var(--muted)]/10 px-3 py-2">
          <summary className="flex cursor-pointer list-none items-center gap-2 text-xs text-[var(--muted-foreground)] [&::-webkit-details-marker]:hidden">
            <ChevronRight className="h-3 w-3 shrink-0 transition-transform group-open/usage:rotate-90" />
            <span className="flex-1">Token usage (turn total)</span>
            <TokenBadge n={estTokens} title={credit_usage?.note} />
          </summary>
          <p className="mt-2 border-t border-[var(--border)]/50 pt-2 text-[11px] text-[var(--muted-foreground)]">
            Estimated total for this orchestrated turn. Per-agent breakdown may be added when the API exposes it.
          </p>
        </details>
      ) : null}
    </section>
  );
}
