"use client";

import { useRef, useState, useEffect } from "react";
import {
  AssistantRuntimeProvider,
  ThreadPrimitive,
  MessagePrimitive,
  ComposerPrimitive,
  AuiIf,
} from "@assistant-ui/react";
import { useChatRuntime, AssistantChatTransport } from "@assistant-ui/react-ai-sdk";
import { GatewayMessageParts } from "@/components/GatewayPartRenderers";
import { GatewayActionProvider, type ActionPayload } from "@/contexts/GatewayActionContext";

const SUGGESTIONS = [
  "Find flowers for delivery",
  "Plan a date night",
  "Best birthday gifts under $50",
];

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

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    setSidebarOpen(mq.matches);
    const handler = () => setSidebarOpen(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);
  const bundleIdRef = useRef<string | null>(null);
  const exploreProductIdRef = useRef<string | null>(null);

  const runtime = useChatRuntime({
    transport: new AssistantChatTransport({
      api: "/api/chat",
      prepareSendMessagesRequest: ({ messages }) => {
        const lastUser = [...messages].reverse().find((m) => m.role === "user") as
          | { content?: unknown; parts?: unknown }
          | undefined;
        const raw =
          lastUser?.content ?? lastUser?.parts;
        const text =
          typeof raw === "string"
            ? raw.trim()
            : Array.isArray(raw)
              ? (raw as { type?: string; text?: string }[])
                  .map((p) => (p?.type === "text" && typeof p?.text === "string" ? p.text : ""))
                  .join("")
                  .trim()
              : "";
        const body: Record<string, unknown> = { text: text || undefined };
        if (bundleIdRef.current) body.bundle_id = bundleIdRef.current;
        const epid = exploreProductIdRef.current;
        if (epid) {
          body.explore_product_id = epid;
          exploreProductIdRef.current = null;
        }
        return { body };
      },
    }),
  });

  const handleAction = async (payload: ActionPayload) => {
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
        setToast(json.summary ?? json.message ?? "Added to bundle.");
      } else if (payload.action === "add_bundle_bulk" && payload.product_ids?.length) {
        const body: Record<string, unknown> = {
          product_ids: payload.product_ids,
          option_label: payload.option_label,
        };
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
        appendAssistant(json.summary ?? json.message ?? "Added bundle.");
      } else if (payload.action === "checkout" && payload.bundle_id) {
        const res = await fetch("/api/checkout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ bundle_id: payload.bundle_id }),
        });
        const json = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(json.error || "Checkout failed");
        appendAssistant(json.summary ?? json.message ?? "Proceeding to checkout.");
      } else if (payload.action === "proceed_to_payment" && payload.order_id) {
        appendAssistant(
          `Order ${payload.order_id} is ready. Proceed to payment when the flow is integrated.`
        );
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
          content: [
            { type: "text" as const, text: `I'd like to explore the ${payload.option_label}` },
          ],
        });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Action failed";
      appendAssistant(`Error: ${msg}`);
    }
  };

  const sendSuggestion = (label: string) => {
    runtime.thread.append({
      role: "user",
      content: [{ type: "text" as const, text: label }],
    });
  };

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <GatewayActionProvider onAction={handleAction}>
        {toast && (
          <div
            role="status"
            className="fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white shadow-lg dark:bg-gray-800"
          >
            {toast}
          </div>
        )}
        <div className="flex h-screen bg-[var(--background)]">
          {/* Sidebar - always visible; collapsed = narrow strip with Atreyai + toggle */}
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
              <span className={`truncate text-sm font-medium ${sidebarOpen ? "" : "hidden"}`}>
                Atreyai
              </span>
              <span className={`text-sm font-semibold text-[var(--sidebar-foreground)] ${sidebarOpen ? "hidden" : ""}`} title="Atreyai">
                A
              </span>
            </div>
            <div className={`flex-1 overflow-y-auto p-2 ${sidebarOpen ? "" : "hidden"}`}>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-white/10"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                New Thread
              </button>
            </div>
          </aside>

          {/* Main chat area */}
          <div className="flex min-w-0 flex-1 flex-col">
            <ThreadPrimitive.Root className="relative flex min-h-0 flex-1 flex-col">
              <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto">
                <div className="mx-auto flex min-h-full max-w-2xl flex-col px-4 pb-4">
                  <AuiIf condition={(s) => s.thread.isEmpty}>
                    <div className="flex flex-1 flex-col items-center justify-center gap-6 py-12">
                      <h2 className="text-2xl font-semibold text-[var(--foreground)]">
                        Hello there!
                      </h2>
                      <p className="text-[var(--muted)]">
                        How can I help you today?
                      </p>
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
                      components={{
                        UserMessage,
                        AssistantMessage,
                      }}
                    />
                  </div>
                  <div className="h-4 shrink-0" />
                </div>
              </ThreadPrimitive.Viewport>

              {/* Scroll to bottom - outside chat view, above composer; hidden when already at bottom */}
              <ThreadPrimitive.ScrollToBottom
                className="absolute bottom-20 left-1/2 z-10 flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--background)] px-4 py-2 text-xs shadow-lg transition-opacity hover:bg-zinc-50 disabled:pointer-events-none disabled:opacity-0 dark:hover:bg-zinc-800"
                aria-label="Scroll to bottom"
              >
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
                <span>Scroll to bottom</span>
              </ThreadPrimitive.ScrollToBottom>

              {/* Composer - ChatGPT-style */}
              <div className="border-t border-[var(--border)] bg-[var(--background)] p-4">
                <div className="mx-auto max-w-2xl">
                  <ComposerPrimitive.Root className="flex items-end gap-2 rounded-2xl border border-[var(--input)] bg-[var(--background)] shadow-sm focus-within:ring-2 focus-within:ring-[var(--ring)]">
                    <button
                      type="button"
                      className="shrink-0 rounded-full p-2 text-[var(--muted)] hover:bg-zinc-100 hover:text-[var(--foreground)] dark:hover:bg-zinc-800"
                      aria-label="Add attachment"
                    >
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
        </div>
      </GatewayActionProvider>
    </AssistantRuntimeProvider>
  );
}
