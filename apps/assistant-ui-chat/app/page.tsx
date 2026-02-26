"use client";

import { useRef, useState, useEffect, useCallback, useMemo } from "react";
import {
  AssistantRuntimeProvider,
  ThreadPrimitive,
  MessagePrimitive,
  ComposerPrimitive,
  AuiIf,
  useThread,
} from "@assistant-ui/react";
import { useChatRuntime, AssistantChatTransport } from "@assistant-ui/react-ai-sdk";
import { GatewayMessageParts } from "@/components/GatewayPartRenderers";
import { GatewayActionProvider, type ActionPayload } from "@/contexts/GatewayActionContext";

const SUGGESTIONS = [
  "Find flowers for delivery",
  "Plan a date night",
  "Best birthday gifts under $50",
];

const STORAGE_ANON = "uso_anonymous_id";
const STORAGE_THREAD = "uso_thread_id";

const hydratedThreadIds = new Set<string>();

function getOrCreateAnonymousId(): string {
  if (typeof window === "undefined") return "";
  let id = sessionStorage.getItem(STORAGE_ANON);
  if (!id) {
    id = `anon_${Date.now()}_${Math.random().toString(36).slice(2, 15)}`;
    sessionStorage.setItem(STORAGE_ANON, id);
  }
  return id;
}

type ThreadItem = { id: string; title: string; has_completed_order: boolean };

function extractThreadMetadataFromMessage(msg: { content?: unknown; parts?: unknown }): { thread_id?: string; thread_title?: string } | null {
  const parts = (msg.content ?? msg.parts) as Array<{ type?: string; name?: string; data?: Record<string, unknown> }> | undefined;
  if (!Array.isArray(parts)) return null;
  const part = parts.find((p) => p?.type === "data" && (p?.name === "thread_metadata" || (p?.data as Record<string, unknown>)?.thread_id));
  const data = (part as { data?: Record<string, unknown> })?.data;
  if (!data || typeof data.thread_id !== "string") return null;
  return { thread_id: data.thread_id as string, thread_title: data.thread_title as string | undefined };
}

function ThreadMetadataListener({
  onMetadata,
}: {
  onMetadata: (payload: { thread_id: string; thread_title?: string }) => void;
}) {
  const messages = useThread((s) => s.messages);
  const lastProcessed = useRef<string | null>(null);
  useEffect(() => {
    const last = [...messages].reverse().find((m) => m.role === "assistant");
    if (!last) return;
    const key = `${last.id ?? "x"}`;
    if (lastProcessed.current === key) return;
    const meta = extractThreadMetadataFromMessage(last as { content?: unknown; parts?: unknown });
    if (meta?.thread_id) {
      lastProcessed.current = key;
      onMetadata(meta as { thread_id: string; thread_title?: string });
    }
  }, [messages, onMetadata]);
  return null;
}

function AssistantMessage() {
  return (
    <MessagePrimitive.Root className="flex justify-start">
      <div className="msg-assistant w-full">
        <GatewayMessageParts />
      </div>
    </MessagePrimitive.Root>
  );
}

function UserMessage() {
  return (
    <MessagePrimitive.Root className="flex justify-end">
      <div className="msg-user w-fit">
        <MessagePrimitive.Parts />
      </div>
    </MessagePrimitive.Root>
  );
}

type LoadedMessage = { id?: string; role: string; content: string; adaptiveCard?: unknown };

function ChatContent({
  threadId,
  initialMessages,
  initialBundleId,
  anonymousId,
  onThreadMetadata,
  onHasBundle,
  hasBundle,
}: {
  threadId: string | null;
  initialMessages: LoadedMessage[];
  initialBundleId: string | null;
  anonymousId: string;
  onThreadMetadata: (p: { thread_id: string; thread_title?: string }) => void;
  onHasBundle: (v: boolean) => void;
  hasBundle: boolean;
}) {
  const bundleIdRef = useRef<string | null>(initialBundleId);
  const exploreProductIdRef = useRef<string | null>(null);
  const orderIdRef = useRef<string | null>(null);
  if (typeof window !== "undefined" && !orderIdRef.current) {
    const saved = sessionStorage.getItem("uso_order_id");
    if (saved) orderIdRef.current = saved;
  }
  if (initialBundleId) bundleIdRef.current = initialBundleId;

  const threadIdRef = useRef(threadId);
  threadIdRef.current = threadId;

  const transport = useMemo(
    () =>
      new AssistantChatTransport({
        api: "/api/chat",
        prepareSendMessagesRequest: ({ messages }) => {
          const lastUser = [...messages].reverse().find((m) => m.role === "user") as { content?: unknown; parts?: unknown } | undefined;
          const raw = lastUser?.content ?? lastUser?.parts;
          const text =
            typeof raw === "string"
              ? raw.trim()
              : Array.isArray(raw)
                ? (raw as { type?: string; text?: string }[])
                    .map((p) => (p?.type === "text" && typeof p?.text === "string" ? p.text : ""))
                    .join("")
                    .trim()
                : "";
          const body: Record<string, unknown> = { text: text || undefined, anonymous_id: anonymousId };
          if (bundleIdRef.current) body.bundle_id = bundleIdRef.current;
          if (orderIdRef.current) body.order_id = orderIdRef.current;
          const tid = threadIdRef.current ?? (typeof window !== "undefined" ? sessionStorage.getItem(STORAGE_THREAD) : null);
          if (tid) body.thread_id = tid;
          const epid = exploreProductIdRef.current;
          if (epid) {
            body.explore_product_id = epid;
            exploreProductIdRef.current = null;
          }
          return { body };
        },
      }),
    [anonymousId]
  );

  const runtime = useChatRuntime({ transport });

  useEffect(() => {
    if (initialMessages.length === 0 || !threadId) return;
    if (hydratedThreadIds.has(threadId)) return;
    hydratedThreadIds.add(threadId);
    for (const m of initialMessages) {
      const content = typeof m.content === "string" ? m.content : String(m.content ?? "");
      if (!content && m.role === "system") continue;
      runtime.thread.append({
        role: m.role as "user" | "assistant" | "system",
        content: [{ type: "text" as const, text: content }],
      });
    }
    return () => {
      hydratedThreadIds.delete(threadId);
    };
  }, [initialMessages, runtime, threadId]);

  const paymentSuccessHandled = useRef(false);
  useEffect(() => {
    if (typeof window === "undefined" || paymentSuccessHandled.current) return;
    const params = new URLSearchParams(window.location.search);
    const orderId = params.get("order_id");
    if (params.get("payment_success") === "1" && orderId) {
      paymentSuccessHandled.current = true;
      orderIdRef.current = orderId;
      sessionStorage.setItem("uso_order_id", orderId);
      const msg = `**Order confirmed!** Thank you for your order.\n\nYour order ID is \`${orderId}\`. You can continue this chat for any questions about your order—customer support has full context.`;
      runtime.thread.append({
        role: "assistant",
        content: [{ type: "text" as const, text: msg }],
      });
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [runtime]);

  const [addConfirmations, setAddConfirmations] = useState<string[]>([]);
  const actionInFlightRef = useRef(false);
  const handleAction = useCallback(
    async (payload: ActionPayload) => {
      if (actionInFlightRef.current) return;
      actionInFlightRef.current = true;
      const appendAssistant = (text: string) => {
        runtime.thread.append({
          role: "assistant",
          content: [{ type: "text" as const, text }],
        });
      };
      try {
        if (payload.action === "add_to_bundle" && payload.product_id) {
          const body: Record<string, string> = { product_id: payload.product_id };
          if (bundleIdRef.current) body.bundle_id = bundleIdRef.current;
          const res = await fetch("/api/bundle/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          const json = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(json.error || "Add to bundle failed");
          const bid = json.bundle_id ?? json.data?.bundle_id;
          if (bid) bundleIdRef.current = bid;
          onHasBundle(true);
          appendAssistant(`${json.summary ?? json.message ?? "Added to bundle."} You can view your bundle anytime or add more items.`);
        } else if (payload.action === "add_bundle_bulk" && payload.product_ids?.length) {
          const body: Record<string, unknown> = { product_ids: payload.product_ids, option_label: payload.option_label };
          if (bundleIdRef.current) body.bundle_id = bundleIdRef.current;
          const res = await fetch("/api/bundle/add-bulk", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          const json = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(json.error || "Bulk add failed");
          const bid = json.bundle_id ?? json.data?.bundle_id;
          if (bid) bundleIdRef.current = bid;
          onHasBundle(true);
          setAddConfirmations((prev) => [...prev, `${json.summary ?? json.message ?? "Added bundle."} You can view your bundle anytime.`]);
        } else if (payload.action === "checkout" && payload.bundle_id) {
          const res = await fetch("/api/checkout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bundle_id: payload.bundle_id }),
          });
          const json = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(json.error || "Checkout failed");
          const orderId = json.order_id ?? json.data?.id;
          if (orderId) {
            orderIdRef.current = orderId;
            sessionStorage.setItem("uso_order_id", orderId);
            runtime.thread.append({
              role: "assistant",
              content: [
                { type: "text" as const, text: json.summary ?? json.message ?? "Your order is ready. Complete your payment below:" },
                { type: "data" as const, name: "payment_form", data: { order_id: orderId } },
              ],
            });
          } else {
            appendAssistant(json.summary ?? json.message ?? "Proceeding to checkout.");
          }
        } else if (payload.action === "proceed_to_payment" && payload.order_id) {
          orderIdRef.current = payload.order_id;
          sessionStorage.setItem("uso_order_id", payload.order_id);
          runtime.thread.append({
            role: "assistant",
            content: [
              { type: "text" as const, text: "Complete your payment below:" },
              { type: "data" as const, name: "payment_form", data: { order_id: payload.order_id } },
            ],
          });
        } else if (payload.action === "explore_product" && payload.product_id) {
          exploreProductIdRef.current = payload.product_id;
          const name = payload.product_name ?? "this product";
          runtime.thread.append({
            role: "user",
            content: [{ type: "text" as const, text: `Tell me more about ${name}` }],
          });
        } else if (payload.action === "explore_theme" && payload.option_label) {
          runtime.thread.append({
            role: "user",
            content: [{ type: "text" as const, text: `I'd like to explore the ${payload.option_label}` }],
          });
        } else if (payload.action === "view_bundle" && payload.bundle_id) {
          runtime.thread.append({
            role: "user",
            content: [{ type: "text" as const, text: "Show me my bundle" }],
          });
        }
      } catch (err) {
        appendAssistant(`Error: ${err instanceof Error ? err.message : "Action failed"}`);
      } finally {
        actionInFlightRef.current = false;
      }
    },
    [runtime, onHasBundle]
  );

  const sendSuggestion = (label: string) => {
    runtime.thread.append({
      role: "user",
      content: [{ type: "text" as const, text: label }],
    });
  };

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <GatewayActionProvider onAction={handleAction}>
        <ThreadMetadataListener onMetadata={onThreadMetadata} />
        <div className="flex min-w-0 flex-1 flex-col">
          <ThreadPrimitive.Root className="relative flex min-h-0 flex-1 flex-col">
            <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto">
              <div className="mx-auto flex min-h-full max-w-2xl flex-col px-4 pb-4">
                <AuiIf condition={(s) => s.thread.isEmpty}>
                  <div className="flex flex-1 flex-col items-center justify-center gap-6 py-12">
                    <h2 className="text-2xl font-semibold text-[var(--foreground)]">Hello there!</h2>
                    <p className="text-[var(--muted)]">How can I help you today?</p>
                    <div className="flex flex-wrap justify-center gap-2">
                      {SUGGESTIONS.map((label, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => sendSuggestion(label)}
                          className="rounded-full border border-[var(--border)] bg-[var(--background)] px-4 py-2.5 text-sm text-[var(--foreground)] shadow-sm transition-colors hover:bg-zinc-100 hover:dark:bg-zinc-800"
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                </AuiIf>
                <div className="flex flex-col gap-4 pt-6">
                  <ThreadPrimitive.Messages
                    components={{ UserMessage, AssistantMessage }}
                  />
                  {addConfirmations.map((text, i) => (
                    <div key={i} className="flex justify-start">
                      <div className="msg-assistant max-w-[85%] rounded-2xl bg-[var(--muted)]/30 px-4 py-2.5 text-sm text-[var(--foreground)]">
                        {text}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="h-4 shrink-0" />
              </div>
            </ThreadPrimitive.Viewport>
            <ThreadPrimitive.ScrollToBottom
              className="absolute bottom-20 left-1/2 z-10 flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--background)] px-4 py-2 text-xs shadow-lg transition-opacity hover:bg-zinc-50 disabled:pointer-events-none disabled:opacity-0 dark:hover:bg-zinc-800"
              aria-label="Scroll to bottom"
            >
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
              </svg>
              <span>Scroll to bottom</span>
            </ThreadPrimitive.ScrollToBottom>
            <div className="border-t border-[var(--border)] bg-[var(--background)] p-4">
              <div className="mx-auto max-w-2xl space-y-2">
                {hasBundle && bundleIdRef.current && (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        handleAction({ action: "view_bundle", bundle_id: bundleIdRef.current! });
                      }}
                      className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-[var(--primary)]/50 bg-[var(--primary)]/10 px-3 py-2 text-sm font-medium text-[var(--primary)] hover:bg-[var(--primary)]/20"
                    >
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8 4-8-4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                      </svg>
                      View bundle
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        handleAction({ action: "checkout", bundle_id: bundleIdRef.current! });
                      }}
                      className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-[var(--primary)] px-3 py-2 text-sm font-medium text-[var(--primary-foreground)] hover:opacity-90"
                    >
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                      </svg>
                      Checkout
                    </button>
                  </div>
                )}
                <ComposerPrimitive.Root className="flex items-end gap-2 rounded-2xl border border-[var(--input)] bg-[var(--background)] shadow-sm focus-within:ring-2 focus-within:ring-[var(--ring)]">
                  <button type="button" className="shrink-0 rounded-full p-2 text-[var(--muted)] hover:bg-zinc-100 hover:text-[var(--foreground)] dark:hover:bg-zinc-800" aria-label="Add attachment">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                    </svg>
                  </button>
                  <ComposerPrimitive.Input
                    placeholder="Message…"
                    className="min-h-12 min-w-0 flex-1 bg-transparent px-2 py-3 text-[var(--foreground)] placeholder:text-[var(--muted)] focus:outline-none"
                  />
                  <AuiIf condition={(s) => !s.thread.isRunning}>
                    <ComposerPrimitive.Send className="shrink-0 rounded-full bg-[var(--primary)] p-2.5 text-[var(--primary-foreground)] hover:opacity-90">
                      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                      </svg>
                    </ComposerPrimitive.Send>
                  </AuiIf>
                  <AuiIf condition={(s) => s.thread.isRunning}>
                    <ComposerPrimitive.Cancel className="shrink-0 rounded-full bg-zinc-500 px-4 py-2.5 text-sm text-white hover:bg-zinc-600">
                      Cancel
                    </ComposerPrimitive.Cancel>
                  </AuiIf>
                </ComposerPrimitive.Root>
              </div>
            </div>
          </ThreadPrimitive.Root>
        </div>
      </GatewayActionProvider>
    </AssistantRuntimeProvider>
  );
}

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [threads, setThreads] = useState<ThreadItem[]>([]);
  const [threadId, setThreadId] = useState<string | null>(() =>
    typeof window !== "undefined" ? sessionStorage.getItem(STORAGE_THREAD) : null
  );
  const [sessionKey, setSessionKey] = useState<string>(() =>
    typeof window !== "undefined"
      ? sessionStorage.getItem(STORAGE_THREAD) ?? `new-${Date.now()}`
      : "new"
  );
  const [loadedThread, setLoadedThread] = useState<{
    id: string;
    messages: LoadedMessage[];
    bundleId: string | null;
  } | null>(null);
  const [hasBundle, setHasBundle] = useState(false);
  const [loadingThread, setLoadingThread] = useState(false);
  const anonymousId = typeof window !== "undefined" ? getOrCreateAnonymousId() : "";
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    setSidebarOpen(mq.matches);
    const handler = () => setSidebarOpen(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const fetchThreads = useCallback(async () => {
    if (!anonymousId) return;
    try {
      const res = await fetch(`/api/threads?anonymous_id=${encodeURIComponent(anonymousId)}`);
      if (!res.ok) return;
      const json = await res.json();
      setThreads(json.threads ?? []);
    } catch {
      // persistence not configured or network error
    }
  }, [anonymousId]);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  const handleNewChat = () => {
    sessionStorage.removeItem(STORAGE_THREAD);
    setThreadId(null);
    setSessionKey(`new-${Date.now()}`);
    setLoadedThread(null);
    setHasBundle(false);
  };

  const handleSelectThread = useCallback(async (id: string) => {
    if (id === threadId && loadedThread?.id === id) return;
    setLoadingThread(true);
    try {
      const res = await fetch(`/api/threads/${id}?anonymous_id=${encodeURIComponent(anonymousId)}`);
      if (!res.ok) throw new Error("Failed to load thread");
      const json = await res.json();
      sessionStorage.setItem(STORAGE_THREAD, id);
      setThreadId(id);
      setSessionKey(id);
      setLoadedThread({
        id,
        messages: json.messages ?? [],
        bundleId: json.thread?.bundle_id ?? null,
      });
      setHasBundle(!!json.thread?.bundle_id);
    } catch {
      // ignore
    } finally {
      setLoadingThread(false);
    }
  }, [threadId, loadedThread?.id, anonymousId]);

  const initialLoadDone = useRef(false);
  const handleSelectThreadRef = useRef(handleSelectThread);
  handleSelectThreadRef.current = handleSelectThread;
  useEffect(() => {
    if (!anonymousId || initialLoadDone.current) return;
    const tid = typeof window !== "undefined" ? sessionStorage.getItem(STORAGE_THREAD) : null;
    if (!tid) return;
    initialLoadDone.current = true;
    handleSelectThreadRef.current(tid);
  }, [anonymousId]);

  const handleDeleteThread = async (id: string) => {
    try {
      const res = await fetch(`/api/threads/${id}?anonymous_id=${encodeURIComponent(anonymousId)}`, { method: "DELETE" });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        alert(json.error ?? "Could not delete");
        return;
      }
      if (threadId === id) handleNewChat();
      fetchThreads();
    } catch {
      alert("Could not delete");
    }
  };

  const handleThreadMetadata = useCallback(
    (p: { thread_id: string; thread_title?: string }) => {
      sessionStorage.setItem(STORAGE_THREAD, p.thread_id);
      setThreadId(p.thread_id);
      fetchThreads();
    },
    [fetchThreads]
  );

  const chatKey = sessionKey;
  const initialMessages = loadedThread?.id === threadId ? loadedThread.messages : [];
  const initialBundleId = loadedThread?.id === threadId ? loadedThread.bundleId : null;

  return (
    <div className="flex h-screen bg-[var(--background)]">
      <aside
        className={`flex shrink-0 flex-col border-r border-[var(--border)] bg-[var(--sidebar)] text-[var(--sidebar-foreground)] transition-[width] duration-200 ease-out ${
          sidebarOpen ? "w-56" : "w-14"
        }`}
      >
        <div className="flex h-14 min-w-0 flex-shrink-0 items-center gap-2 border-b border-[var(--border)] px-2">
          <button
            type="button"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="flex shrink-0 items-center justify-center rounded p-2 hover:bg-white/10"
            aria-label={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {sidebarOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
              )}
            </svg>
          </button>
          <span className={`truncate text-sm font-medium ${sidebarOpen ? "" : "hidden"}`}>Atreyai</span>
          <span className={`text-sm font-semibold ${sidebarOpen ? "hidden" : ""}`} title="Atreyai">A</span>
        </div>
        <div className={`flex-1 overflow-y-auto p-2 ${sidebarOpen ? "" : "hidden"}`}>
          <button
            type="button"
            onClick={handleNewChat}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-white/10"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New chat
          </button>
          <div className="mt-2 min-h-0 flex-1">
            <p className="mb-2 px-2 text-xs font-medium uppercase tracking-wider text-[var(--muted)]">Conversations</p>
            {loadingThread ? (
              <p className="px-3 py-2 text-sm text-[var(--muted)]">Loading…</p>
            ) : (
              <ul className="space-y-0.5">
                {threads.map((t) => (
                  <li key={t.id}>
                    <div className="group flex items-center gap-1 rounded-lg hover:bg-[var(--border)]/50">
                      <button
                        type="button"
                        onClick={() => handleSelectThread(t.id)}
                        className={`min-w-0 flex-1 truncate px-3 py-2 text-left text-sm ${
                          threadId === t.id ? "font-medium text-[var(--primary)]" : "text-[var(--foreground)]"
                        }`}
                      >
                        {(t.title || "Chat").length > 28 ? (t.title || "Chat").slice(0, 25) + "…" : t.title || "Chat"}
                      </button>
                      {!t.has_completed_order && (
                        <button
                          type="button"
                          onClick={() => handleDeleteThread(t.id)}
                          aria-label="Delete conversation"
                          className="rounded p-1.5 text-[var(--muted)] opacity-0 transition-opacity hover:bg-red-500/20 hover:text-red-500 group-hover:opacity-100"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </aside>
      <div key={chatKey} className="flex min-w-0 flex-1 flex-col">
        <ChatContent
          threadId={threadId}
          initialMessages={initialMessages}
          initialBundleId={initialBundleId}
          anonymousId={anonymousId}
          onThreadMetadata={handleThreadMetadata}
          onHasBundle={setHasBundle}
          hasBundle={hasBundle}
        />
      </div>
    </div>
  );
}
