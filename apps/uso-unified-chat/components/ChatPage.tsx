"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AdaptiveCardRenderer, type ActionPayload } from "@/components/AdaptiveCardRenderer";
import { PaymentModal } from "@/components/PaymentModal";

type Provider = "chatgpt" | "gemini";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content?: string;
  adaptiveCard?: Record<string, unknown>;
};

const E2E_ACTIONS = ["add_to_bundle", "view_bundle", "remove_from_bundle", "checkout", "complete_checkout"];

function filterE2EActions(card: Record<string, unknown>, e2eEnabled: boolean): Record<string, unknown> {
  if (e2eEnabled) return card;
  const out = JSON.parse(JSON.stringify(card)) as Record<string, unknown>;
  const filter = (obj: unknown): unknown => {
    if (!obj || typeof obj !== "object") return obj;
    const o = obj as Record<string, unknown>;
    if (Array.isArray(o.actions)) {
      o.actions = (o.actions as Array<Record<string, unknown>>)
        .filter((a) => {
          const d = a.data as Record<string, unknown> | undefined;
          const act = d?.action as string | undefined;
          return !act || !E2E_ACTIONS.includes(act);
        })
        .map(filter) as unknown[];
    }
    if (Array.isArray(o.body)) {
      o.body = (o.body as unknown[]).map(filter);
    }
    if (Array.isArray(o.items)) {
      o.items = (o.items as unknown[]).map(filter);
    }
    return o;
  };
  return filter(out) as Record<string, unknown>;
}

function useSessionId() {
  const [id] = useState(() =>
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `session-${Date.now()}`
  );
  return id;
}

const STRIPE_CONFIGURED = !!(
  typeof process !== "undefined" &&
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
);

export type ChatPageProps = {
  partnerId?: string;
  e2eEnabled?: boolean;
  welcomeMessage?: string;
  /** When set, programmatically send this prompt. Cleared via onPromptSent. */
  promptToSend?: string;
  /** Called after promptToSend has been sent. Parent should clear promptToSend. */
  onPromptSent?: () => void;
  /** Hide header when embedded in landing page */
  embeddedInLanding?: boolean;
  /** When user returns from Stripe with payment_success, add confirmation message */
  paymentSuccessOrderId?: string | null;
  /** Called after payment success message is shown. Parent should clear URL params. */
  onPaymentSuccessHandled?: () => void;
};

export function ChatPage(props: ChatPageProps = {}) {
  const {
    partnerId,
    e2eEnabled: e2eProp,
    welcomeMessage,
    promptToSend,
    onPromptSent,
    embeddedInLanding,
    paymentSuccessOrderId,
    onPaymentSuccessHandled,
  } = props;
  const [provider, setProvider] = useState<Provider>("chatgpt");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [paymentOrderId, setPaymentOrderId] = useState<string | null>(null);
  const e2eEnabled = e2eProp ?? true;
  const sessionId = useSessionId();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = useCallback(
    (msg: Omit<ChatMessage, "id">) => {
      setMessages((prev) => [
        ...prev,
        { ...msg, id: `msg-${Date.now()}-${Math.random().toString(36).slice(2)}` },
      ]);
    },
    []
  );

  const sendMessage = useCallback(
    async (userMessage: string, fromPrompt = false) => {
      if (!userMessage.trim() || loading) return;
      setInput("");
      addMessage({ role: "user", content: userMessage });
      setLoading(true);
      try {
        const payload: Record<string, unknown> = {
          provider,
          messages: [...messages, { role: "user", content: userMessage }].map(
            (m) => ({ role: m.role, content: m.content ?? "" })
          ),
        };
        if (partnerId) payload.partner_id = partnerId;
        if (sessionId) payload.user_id = sessionId;

        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        type ChatResponse = {
          data?: {
            products?: { products?: Array<{ name?: string; price?: number }>; count?: number };
            text?: string;
            error?: string;
          };
          summary?: string;
          message?: string;
          error?: string;
          adaptive_card?: Record<string, unknown>;
        };
        let data: ChatResponse;
        try {
          data = (await res.json()) as ChatResponse;
        } catch {
          throw new Error(res.ok ? "Invalid response" : `HTTP ${res.status}`);
        }
        if (!res.ok) {
          const errMsg = data?.error || `HTTP ${res.status}`;
          throw new Error(errMsg);
        }

        const productList = data.data?.products?.products ?? [];
        const assistantContent =
          data.summary ??
          (productList.length > 0
            ? `Found ${productList.length} products`
            : data.data?.text ?? data.message ?? JSON.stringify(data));

        addMessage({
          role: "assistant",
          content: assistantContent,
          adaptiveCard: data.adaptive_card,
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        addMessage({ role: "assistant", content: `Error: ${msg}` });
      } finally {
        setLoading(false);
        if (fromPrompt) onPromptSent?.();
      }
    },
    [addMessage, loading, messages, partnerId, provider, sessionId, onPromptSent]
  );

  const lastSentPromptRef = useRef<string | null>(null);
  useEffect(() => {
    const prompt = promptToSend?.trim();
    if (!prompt || prompt === lastSentPromptRef.current) return;
    lastSentPromptRef.current = prompt;
    sendMessage(prompt, true);
  }, [promptToSend, sendMessage]);
  useEffect(() => {
    if (!promptToSend?.trim()) lastSentPromptRef.current = null;
  }, [promptToSend]);

  useEffect(() => {
    if (paymentSuccessOrderId) {
      addMessage({
        role: "assistant",
        content: "Payment confirmed! Thank you for your order.",
      });
      onPaymentSuccessHandled?.();
    }
  }, [paymentSuccessOrderId, addMessage, onPaymentSuccessHandled]);

  const handleAction = useCallback(
    async (data: ActionPayload) => {
      const action = data.action;
      if (!action) return;
      if (E2E_ACTIONS.includes(action) && !e2eEnabled) return;

      setLoading(true);
      try {
        if (action === "add_to_bundle" && data.product_id) {
          const res = await fetch("/api/bundle/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              product_id: data.product_id,
              user_id: sessionId,
            }),
          });
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Add to bundle failed");
          addMessage({
            role: "assistant",
            content: json.summary || "Added to bundle.",
            adaptiveCard: json.adaptive_card,
          });
          if (json.adaptive_card) return;
        }

        if (action === "view_bundle" && data.bundle_id) {
          const res = await fetch(`/api/bundles/${data.bundle_id}`);
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Bundle not found");
          addMessage({
            role: "assistant",
            content: json.summary,
            adaptiveCard: json.adaptive_card,
          });
          return;
        }

        if (action === "remove_from_bundle" && data.item_id) {
          const res = await fetch("/api/bundle/remove", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ item_id: data.item_id }),
          });
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Remove failed");
          addMessage({
            role: "assistant",
            content: json.summary || "Item removed.",
          });
          return;
        }

        if (action === "checkout" && data.bundle_id) {
          const res = await fetch("/api/checkout", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bundle_id: data.bundle_id }),
          });
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Checkout failed");
          addMessage({
            role: "assistant",
            content: json.summary,
            adaptiveCard: json.adaptive_card,
          });
          return;
        }

        if (action === "complete_checkout" && data.order_id) {
          if (STRIPE_CONFIGURED) {
            setPaymentOrderId(data.order_id);
            return;
          }
          const res = await fetch("/api/payment/confirm", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ order_id: data.order_id }),
          });
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Payment failed");
          addMessage({
            role: "assistant",
            content: json.message || "Payment confirmed! Thank you for your order.",
          });
          return;
        }

        if (action === "add_more") {
          addMessage({
            role: "assistant",
            content: "What else would you like to add? Try searching for more products.",
          });
          return;
        }

        if (action === "view_details" && data.product_id) {
          const res = await fetch(`/api/products/${data.product_id}`);
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Product not found");
          addMessage({
            role: "assistant",
            content: `${json.data?.name || "Product"} — ${json.data?.currency || "USD"} ${Number(json.data?.price || 0).toFixed(2)}`,
          });
          return;
        }
      } catch (err) {
        addMessage({
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : String(err)}`,
        });
      } finally {
        setLoading(false);
      }
    },
    [addMessage, e2eEnabled, sessionId, setPaymentOrderId]
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    sendMessage(input.trim(), false);
  }

  return (
    <div className={`flex flex-col bg-[var(--background)] text-[var(--foreground)] ${embeddedInLanding ? "min-h-[60vh]" : "h-screen"}`}>
      {!embeddedInLanding && (
        <header className="flex-shrink-0 border-b border-[var(--border)] px-4 py-3">
          <div className="max-w-3xl mx-auto flex items-center justify-between">
            <h1 className="text-lg font-semibold">USO Unified Chat</h1>
            <div className="flex items-center gap-3">
              <label className="text-sm text-slate-400">Provider</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value as Provider)}
                disabled={loading}
                className="bg-[var(--card)] border border-[var(--border)] rounded-lg px-3 py-1.5 text-sm"
              >
                <option value="chatgpt">ChatGPT</option>
                <option value="gemini">Gemini</option>
              </select>
            </div>
          </div>
        </header>
      )}

      <main className={`flex-1 overflow-y-auto px-4 py-6 ${embeddedInLanding ? "border border-[var(--border)] rounded-xl" : ""}`}>
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-12 text-slate-400"
            >
              <p className="text-lg mb-2">{welcomeMessage ?? "How can I help you today?"}</p>
              <p className="text-sm">
                Try: &quot;Find me flowers&quot; or &quot;I want chocolates&quot;
              </p>
            </motion.div>
          )}

          <AnimatePresence mode="popLayout">
            {messages.map((m) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                    m.role === "user"
                      ? "bg-[var(--primary-color)] text-[var(--primary-foreground)]"
                      : "bg-[var(--card)] border border-[var(--border)]"
                  }`}
                >
                  {m.content && (
                    <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                  )}
                  {m.adaptiveCard && (
                    <div className="mt-3">
                      <AdaptiveCardRenderer
                        card={filterE2EActions(m.adaptiveCard, e2eEnabled)}
                        onAction={handleAction}
                      />
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-[var(--card)] border border-[var(--border)] rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      {paymentOrderId && (
        <PaymentModal
          orderId={paymentOrderId}
          onClose={() => setPaymentOrderId(null)}
          onSuccess={() => {
            addMessage({
              role: "assistant",
              content: "Payment confirmed! Thank you for your order.",
            });
            setPaymentOrderId(null);
          }}
        />
      )}

      <footer className="flex-shrink-0 border-t border-[var(--border)] px-4 py-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message..."
              disabled={loading}
              className="flex-1 bg-[var(--card)] border border-[var(--border)] rounded-xl px-4 py-3 text-sm placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-[var(--primary-color)]"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-[var(--primary-color)] text-[var(--primary-foreground)] rounded-xl font-medium text-sm hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              Send
            </button>
          </div>
        </form>
      </footer>
    </div>
  );
}
