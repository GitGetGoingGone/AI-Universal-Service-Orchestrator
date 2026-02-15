"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const FLIP_WORDS = ["Discover", "Bundle", "Plan", "Payment"];
const SUGGESTIONS = [
  "Find flowers for delivery",
  "Plan a date night",
  "Best birthday gifts under $50",
  "Show me chocolates",
];

function FlipWord() {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const t = setInterval(() => {
      setIndex((i) => (i + 1) % FLIP_WORDS.length);
    }, 2000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="relative h-12 overflow-hidden sm:h-14">
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={FLIP_WORDS[index]}
          initial={{ y: 24, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -24, opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="absolute inset-x-0 flex items-center justify-center text-2xl font-semibold text-[var(--primary-color)] sm:text-3xl"
        >
          {FLIP_WORDS[index]}
        </motion.span>
      </AnimatePresence>
    </div>
  );
}
import { useAuthState, AuthButtons } from "@/components/AuthWrapper";
import { ConnectWhatsApp } from "@/components/ConnectWhatsApp";
import { AdaptiveCardRenderer, type ActionPayload } from "@/components/AdaptiveCardRenderer";
import { PaymentModal } from "@/components/PaymentModal";
import { SideNav } from "@/components/SideNav";

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
  /** Show left nav pane (Gemini-style). Default true when not embedded. */
  showSideNav?: boolean;
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
    showSideNav: showSideNavProp,
    paymentSuccessOrderId,
    onPaymentSuccessHandled,
  } = props;
  const showSideNav = showSideNavProp ?? !embeddedInLanding;
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

  const prevLoadedThreadIdRef = useRef<string | null>(null);
  useEffect(() => {
    if (!hydrated || !threadId) return;
    if (prevLoadedThreadIdRef.current === threadId) return;
    prevLoadedThreadIdRef.current = threadId;
    const authParam = userId
      ? `user_id=${encodeURIComponent(userId)}`
      : anonymousId
        ? `anonymous_id=${encodeURIComponent(anonymousId)}`
        : null;
    if (!authParam) return;
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

  const [threads, setThreads] = useState<Array<{ id: string; title: string; updated_at: string }>>([]);
  const fetchThreads = useCallback(() => {
    const url = userId ? "/api/threads" : anonymousId ? `/api/threads?anonymous_id=${encodeURIComponent(anonymousId)}` : null;
    if (!url) return;
    fetch(url)
      .then((r) => r.json())
      .then((d) => setThreads(d.threads ?? []))
      .catch(() => setThreads([]));
  }, [userId, anonymousId]);
  useEffect(() => {
    if (userId || anonymousId) fetchThreads();
  }, [userId, anonymousId, fetchThreads]);

  const handleSelectThread = useCallback(
    (id: string | null) => {
      prevLoadedThreadIdRef.current = null;
      setThreadId(id);
      setMessages([]);
      setPendingApprovals([]);
      if (!id) setBundleId(null);
    },
    [setThreadId, setBundleId]
  );

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
        if (newThreadId && !threadId) {
          setThreadId(newThreadId);
          fetchThreads();
        }

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
    [addMessage, loading, messages, partnerId, sessionId, threadId, anonymousId, setThreadId, onPromptSent, userId, fetchThreads]
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

        if (action === "add_to_favorites" && data.product_id) {
          const favPayload: Record<string, string> = {
            item_type: "product",
            item_id: data.product_id,
            item_name: typeof data.product_name === "string" ? data.product_name : "",
          };
          if (!userId && anonymousId) favPayload.anonymous_id = anonymousId;
          const res = await fetch("/api/my-stuff/favorites", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(favPayload),
          });
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Failed to save");
          addMessage({
            role: "assistant",
            content: "Saved to My Stuff!",
          });
          window.dispatchEvent(new Event("my-stuff-refresh"));
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

  const chatContent = (
    <div className={`flex flex-col bg-[var(--background)] text-[var(--foreground)] ${showSideNav ? "min-h-0 flex-1" : embeddedInLanding ? "min-h-[60vh]" : "h-screen"}`}>
      {!embeddedInLanding && !showSideNav && (
        <header className="flex-shrink-0 border-b border-[var(--border)] px-4 py-3">
          <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <h1 className="text-lg font-semibold shrink-0">USO Unified Chat</h1>
              {(userId || anonymousId) && threads.length > 0 && (
                <select
                  value={threadId ?? ""}
                  onChange={(e) => handleSelectThread(e.target.value || null)}
                  className="text-sm px-2 py-1.5 rounded border border-[var(--border)] bg-[var(--card)] max-w-[180px] truncate"
                >
                  <option value="">New chat</option>
                  {threads.map((t) => (
                    <option key={t.id} value={t.id} title={t.title}>
                      {t.title.length > 24 ? t.title.slice(0, 21) + "…" : t.title}
                    </option>
                  ))}
                </select>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <ConnectWhatsApp />
              <AuthButtons />
            </div>
          </div>
        </header>
      )}

      <main
        className={`chat-window flex-1 overflow-y-auto px-4 py-6 ${embeddedInLanding ? "border border-[var(--border)] rounded-xl" : ""} ${messages.length === 0 ? "flex flex-col justify-center" : ""}`}
      >
        <div className={`mx-auto space-y-6 ${messages.length === 0 ? "flex w-full max-w-2xl flex-col items-center" : "max-w-3xl"}`}>
          {embeddedInLanding && (userId || anonymousId) && threads.length > 0 && (
            <div className="flex justify-end">
              <select
                value={threadId ?? ""}
                onChange={(e) => handleSelectThread(e.target.value || null)}
                className="text-sm px-2 py-1.5 rounded border border-[var(--border)] bg-[var(--card)]"
              >
                <option value="">New chat</option>
                {threads.map((t) => (
                  <option key={t.id} value={t.id}>{t.title.length > 30 ? t.title.slice(0, 27) + "…" : t.title}</option>
                ))}
              </select>
            </div>
          )}
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
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4 }}
              className="flex w-full flex-col items-center text-center"
            >
              <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl md:text-5xl">
                Discover, bundle, and order —{" "}
                <span className="text-[var(--primary-color)]">in one conversation</span>
              </h2>
              <p className="mt-2 text-lg text-slate-300">
                {welcomeMessage ?? "Find products, add to cart, and pay — all through chat."}
              </p>
              <div className="mt-6">
                <FlipWord />
              </div>
              <form onSubmit={handleSubmit} className="mt-8 w-full max-w-xl">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type a message..."
                    disabled={loading}
                    className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 text-sm text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[var(--primary-color)]"
                  />
                  <button
                    type="submit"
                    disabled={loading}
                    className="rounded-xl bg-[var(--primary-color)] px-6 py-3 text-sm font-medium text-[var(--primary-foreground)] transition-opacity hover:opacity-90 disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => sendMessage(prompt, true)}
                      className="rounded-full border border-[var(--border)] bg-[var(--card)] px-4 py-2 text-sm text-[var(--card-foreground)] transition-colors hover:border-[var(--primary-color)]/50 hover:bg-[var(--primary-color)]/10"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </form>
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
                <div className="flex flex-col gap-1">
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      m.role === "user"
                        ? "bg-[var(--primary-color)] text-[var(--primary-foreground)]"
                        : "bg-[var(--card)] border border-[var(--border)] text-[var(--card-foreground)]"
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
                  {m.role === "assistant" && (
                    <div className="flex items-center gap-1 pl-1">
                      <button
                        type="button"
                        aria-label="Like"
                        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-[var(--border)] hover:text-white"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        aria-label="Dislike"
                        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-[var(--border)] hover:text-white"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        aria-label="Regenerate"
                        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-[var(--border)] hover:text-white"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        aria-label="Copy"
                        onClick={() => {
                          const text = m.content || (m.adaptiveCard ? JSON.stringify(m.adaptiveCard) : "");
                          if (text) navigator.clipboard?.writeText(text);
                        }}
                        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-[var(--border)] hover:text-white"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        aria-label="More options"
                        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-[var(--border)] hover:text-white"
                      >
                        <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z" />
                        </svg>
                      </button>
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className="flex justify-start"
            >
              <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] px-4 py-3">
                <div className="flex items-center gap-1">
                  <span className="inline-block h-2 w-2 animate-typing-1 rounded-full bg-slate-400" />
                  <span className="inline-block h-2 w-2 animate-typing-2 rounded-full bg-slate-400" />
                  <span className="inline-block h-2 w-2 animate-typing-3 rounded-full bg-slate-400" />
                  <span className="ml-1 h-4 w-0.5 animate-pulse rounded-sm bg-slate-400" aria-hidden />
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

      <AnimatePresence>
        {messages.length > 0 && (
          <motion.footer
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="chat-window flex-shrink-0 border-t border-[var(--border)] px-4 py-4"
          >
          <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
            <div className="mb-3 flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => sendMessage(prompt, true)}
                  className="rounded-full border border-[var(--border)] bg-[var(--card)] px-4 py-2 text-sm text-[var(--card-foreground)] transition-colors hover:border-[var(--primary-color)]/50 hover:bg-[var(--primary-color)]/10"
                >
                  {prompt}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message..."
              disabled={loading}
              className="flex-1 rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 text-sm text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[var(--primary-color)]"
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded-xl bg-[var(--primary-color)] px-6 py-3 text-sm font-medium text-[var(--primary-foreground)] transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </form>
          </motion.footer>
        )}
      </AnimatePresence>
    </div>
  );

  if (showSideNav) {
    return (
      <div className="flex h-screen bg-[var(--background)]">
        <SideNav
          threadId={threadId}
          threads={threads}
          onNewChat={() => handleSelectThread(null)}
          onSelectThread={handleSelectThread}
          hasUserOrAnonymous={!!(userId || anonymousId)}
          anonymousId={anonymousId ?? undefined}
        />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <header className="flex flex-shrink-0 items-center justify-end border-b border-[var(--border)] px-4 py-3">
            <AuthButtons />
          </header>
          <div className="min-h-0 flex-1 overflow-hidden">
            {chatContent}
          </div>
        </div>
      </div>
    );
  }

  return chatContent;
}
