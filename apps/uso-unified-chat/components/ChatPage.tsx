"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAuthState, AuthButtons } from "@/components/AuthWrapper";
import { ConnectWhatsApp } from "@/components/ConnectWhatsApp";
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
const STANDING_INTENT_ACTION = "approve_standing_intent";

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

const STORAGE_KEY_THREAD = "uso_thread_id";
const STORAGE_KEY_ANONYMOUS = "uso_anonymous_id";
const STORAGE_KEY_BUNDLE = "uso_bundle_id";

function useThreadPersistence() {
  const [threadId, setThreadIdState] = useState<string | null>(null);
  const [anonymousId, setAnonymousIdState] = useState<string | null>(null);
  const [bundleId, setBundleIdState] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const t = localStorage.getItem(STORAGE_KEY_THREAD);
    const a = localStorage.getItem(STORAGE_KEY_ANONYMOUS);
    const b = localStorage.getItem(STORAGE_KEY_BUNDLE);
    if (t) setThreadIdState(t);
    if (a) setAnonymousIdState(a);
    else {
      const newA =
        typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : `anon-${Date.now()}`;
      setAnonymousIdState(newA);
      localStorage.setItem(STORAGE_KEY_ANONYMOUS, newA);
    }
    if (b) setBundleIdState(b);
    setHydrated(true);
  }, []);

  const setThreadId = useCallback((id: string | null) => {
    setThreadIdState(id);
    if (typeof window !== "undefined") {
      if (id) localStorage.setItem(STORAGE_KEY_THREAD, id);
      else localStorage.removeItem(STORAGE_KEY_THREAD);
    }
  }, []);

  const setBundleId = useCallback((id: string | null) => {
    setBundleIdState(id);
    if (typeof window !== "undefined") {
      if (id) localStorage.setItem(STORAGE_KEY_BUNDLE, id);
      else localStorage.removeItem(STORAGE_KEY_BUNDLE);
    }
  }, []);

  return {
    threadId,
    anonymousId: anonymousId ?? undefined,
    bundleId,
    setThreadId,
    setBundleId,
    hydrated,
  };
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
  const [pendingApprovals, setPendingApprovals] = useState<
    Array<{ id: string; intent_description: string }>
  >([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [paymentOrderId, setPaymentOrderId] = useState<string | null>(null);
  const e2eEnabled = e2eProp ?? true;
  const sessionId = useSessionId();
  const { isSignedIn } = useAuthState();
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    if (!isSignedIn) {
      setUserId(null);
      return;
    }
    fetch("/api/users/me")
      .then((r) => r.json())
      .then((data) => setUserId(data.user_id ?? null))
      .catch(() => setUserId(null));
  }, [isSignedIn]);

  const {
    threadId,
    anonymousId,
    bundleId,
    setThreadId,
    setBundleId,
    hydrated,
  } = useThreadPersistence();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const hasLoadedThreadRef = useRef(false);
  useEffect(() => {
    if (!hydrated || !threadId || hasLoadedThreadRef.current) return;
    const authParam = userId
      ? `user_id=${encodeURIComponent(userId)}`
      : anonymousId
        ? `anonymous_id=${encodeURIComponent(anonymousId)}`
        : null;
    if (!authParam) return;
    hasLoadedThreadRef.current = true;
    fetch(`/api/threads/${threadId}?${authParam}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.error) return;
        const msgs = (data.messages ?? []).map(
          (m: { id: string; role: string; content?: string; adaptiveCard?: Record<string, unknown> }) => ({
            id: m.id,
            role: m.role as "user" | "assistant",
            content: m.content,
            adaptiveCard: m.adaptiveCard,
          })
        );
        setMessages(msgs);
        if (data.thread?.bundle_id) setBundleId(data.thread.bundle_id);
        setPendingApprovals(data.pending_approvals ?? []);
      })
      .catch(() => {});
  }, [hydrated, threadId, anonymousId, userId, setBundleId]);

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
        if (threadId) {
          payload.thread_id = threadId;
          if (userId) payload.user_id = userId;
          else payload.anonymous_id = anonymousId;
        } else if (userId) {
          payload.user_id = userId;
        } else if (anonymousId) {
          payload.anonymous_id = anonymousId;
        } else {
          payload.user_id = sessionId;
        }

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

        const newThreadId = (data as { thread_id?: string }).thread_id;
        if (newThreadId && !threadId) setThreadId(newThreadId);

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
    [addMessage, loading, messages, partnerId, provider, sessionId, threadId, anonymousId, setThreadId, onPromptSent]
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

      if (action === STANDING_INTENT_ACTION && data.standing_intent_id) {
        setLoading(true);
        try {
          const res = await fetch(
            `/api/standing-intents/${data.standing_intent_id}/approve`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ approved: data.approved !== false }),
            }
          );
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Approve failed");
          setPendingApprovals((prev) =>
            prev.filter((a) => a.id !== data.standing_intent_id)
          );
          addMessage({
            role: "assistant",
            content:
              json.approved !== false
                ? "Standing intent approved. We'll notify you when it's ready."
                : "Standing intent rejected.",
          });
        } catch (err) {
          addMessage({
            role: "assistant",
            content: `Error: ${err instanceof Error ? err.message : String(err)}`,
          });
        } finally {
          setLoading(false);
        }
        return;
      }

      setLoading(true);
      try {
        if (action === "add_to_bundle" && data.product_id) {
          const addPayload: Record<string, string> = {
            product_id: data.product_id,
          };
          if (bundleId) addPayload.bundle_id = bundleId;

          const res = await fetch("/api/bundle/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(addPayload),
          });
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Add to bundle failed");

          const newBundleId = json.bundle_id ?? json.data?.bundle_id;
          if (newBundleId && threadId) {
            setBundleId(newBundleId);
            const patchBody = userId
              ? { bundle_id: newBundleId, user_id: userId }
              : { bundle_id: newBundleId, anonymous_id: anonymousId };
            fetch(`/api/threads/${threadId}`, {
              method: "PATCH",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(patchBody),
            }).catch(() => {});
          } else if (newBundleId) {
            setBundleId(newBundleId);
          }

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
    [addMessage, e2eEnabled, sessionId, setPaymentOrderId, threadId, anonymousId, bundleId, setBundleId, setPendingApprovals, userId]
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
            <div className="flex items-center gap-2">
              <ConnectWhatsApp />
              <AuthButtons />
            </div>
          </div>
        </header>
      )}

      <main className={`flex-1 overflow-y-auto px-4 py-6 ${embeddedInLanding ? "border border-[var(--border)] rounded-xl" : ""}`}>
        <div className="max-w-3xl mx-auto space-y-6">
          {pendingApprovals.length > 0 && (
            <div className="space-y-4">
              <p className="text-sm text-[var(--muted)] font-medium">Pending approvals</p>
              {pendingApprovals.map((a) => {
                const card: Record<string, unknown> = {
                  type: "AdaptiveCard",
                  $schema: "http://adaptivecards.io/schemas/adaptive-card.json",
                  version: "1.5",
                  body: [
                    { type: "TextBlock", text: "Standing Intent Approval", weight: "Bolder", size: "Medium" },
                    { type: "TextBlock", text: a.intent_description, wrap: true },
                  ],
                  actions: [
                    {
                      type: "Action.Submit",
                      title: "Approve",
                      data: {
                        action: STANDING_INTENT_ACTION,
                        standing_intent_id: a.id,
                        approved: true,
                      },
                    },
                    {
                      type: "Action.Submit",
                      title: "Reject",
                      data: {
                        action: STANDING_INTENT_ACTION,
                        standing_intent_id: a.id,
                        approved: false,
                      },
                    },
                  ],
                };
                return (
                  <div key={a.id} className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4">
                    <AdaptiveCardRenderer card={card} onAction={handleAction} />
                  </div>
                );
              })}
            </div>
          )}
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
