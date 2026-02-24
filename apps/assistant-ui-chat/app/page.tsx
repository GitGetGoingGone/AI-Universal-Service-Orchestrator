"use client";

import { useRef } from "react";
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
    <MessagePrimitive.Root>
      <GatewayMessageParts />
    </MessagePrimitive.Root>
  );
}

function UserMessage() {
  return (
    <MessagePrimitive.Root>
      <MessagePrimitive.Parts />
    </MessagePrimitive.Root>
  );
}

export default function ChatPage() {
  const runtime = useChatRuntime({
    transport: new AssistantChatTransport({
      api: "/api/chat",
    }),
  });

  const bundleIdRef = useRef<string | null>(null);

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
        appendAssistant(json.summary ?? json.message ?? "Added to bundle.");
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
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Action failed";
      appendAssistant(`Error: ${msg}`);
    }
  };

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <GatewayActionProvider onAction={handleAction}>
        <div className="mx-auto flex h-screen max-w-2xl flex-col bg-white dark:bg-gray-900">
          <header className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
              Assistant UI Chat
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Gateway:{" "}
              {process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8002"}
            </p>
          </header>

          <ThreadPrimitive.Root className="flex min-h-0 flex-1 flex-col">
            <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto p-4">
              <AuiIf condition={(s) => s.thread.isEmpty}>
                <div className="flex flex-col gap-4 py-8">
                  <p className="text-center text-gray-600 dark:text-gray-400">
                    Send a message to discover products and plan gifts.
                  </p>
                  <div className="flex flex-wrap justify-center gap-2">
                    {SUGGESTIONS.map((label, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() =>
                          runtime.thread.append({
                            role: "user",
                            content: [{ type: "text" as const, text: label }],
                          })
                        }
                        className="rounded-full border border-gray-300 bg-gray-50 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </AuiIf>
              <ThreadPrimitive.Messages
                components={{
                  UserMessage,
                  AssistantMessage,
                }}
              />
              <ThreadPrimitive.ScrollToBottom />
            </ThreadPrimitive.Viewport>

            <div className="border-t border-gray-200 p-3 dark:border-gray-700">
              <ComposerPrimitive.Root className="flex gap-2">
                <ComposerPrimitive.Input
                  placeholder="Type a message..."
                  className="min-w-0 flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-900 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-400"
                />
                <AuiIf condition={(s) => !s.thread.isRunning}>
                  <ComposerPrimitive.Send className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700">
                    Send
                  </ComposerPrimitive.Send>
                </AuiIf>
                <AuiIf condition={(s) => s.thread.isRunning}>
                  <ComposerPrimitive.Cancel className="rounded-lg bg-gray-500 px-4 py-2 font-medium text-white hover:bg-gray-600">
                    Cancel
                  </ComposerPrimitive.Cancel>
                </AuiIf>
              </ComposerPrimitive.Root>
            </div>
          </ThreadPrimitive.Root>
        </div>
      </GatewayActionProvider>
    </AssistantRuntimeProvider>
  );
}
