/** Session queue: agent ids to skip on the next multi-agent run (user_cancellable agents). */
export const CHAT_STORAGE_MA_CANCEL_NEXT = "uso_ma_cancel_next";

/** Dispatched on `window` when the queue is updated or consumed so UI can re-sync. */
export const MA_CANCEL_QUEUE_CHANGED_EVENT = "uso-ma-cancel-queue-changed";

export function readMaCancelNextQueue(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(CHAT_STORAGE_MA_CANCEL_NEXT);
    if (!raw) return [];
    const p = JSON.parse(raw) as unknown;
    return Array.isArray(p) ? p.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function queueMaCancelNext(agentId: string): void {
  if (typeof window === "undefined" || !agentId) return;
  const cur = new Set(readMaCancelNextQueue());
  cur.add(agentId);
  sessionStorage.setItem(CHAT_STORAGE_MA_CANCEL_NEXT, JSON.stringify([...cur]));
}

export function unqueueMaCancelNext(agentId: string): void {
  if (typeof window === "undefined" || !agentId) return;
  const cur = new Set(readMaCancelNextQueue());
  cur.delete(agentId);
  if (cur.size === 0) sessionStorage.removeItem(CHAT_STORAGE_MA_CANCEL_NEXT);
  else sessionStorage.setItem(CHAT_STORAGE_MA_CANCEL_NEXT, JSON.stringify([...cur]));
}

/** Read and clear the queue (e.g. once per outbound chat request). */
export function takeMaCancelNextForSend(): string[] {
  if (typeof window === "undefined") return [];
  const ids = readMaCancelNextQueue();
  sessionStorage.removeItem(CHAT_STORAGE_MA_CANCEL_NEXT);
  window.dispatchEvent(new CustomEvent(MA_CANCEL_QUEUE_CHANGED_EVENT));
  return ids;
}
