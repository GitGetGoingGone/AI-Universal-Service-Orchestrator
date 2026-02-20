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
import ReactMarkdown from "react-markdown";
import { useAuthState, hasClerk } from "@/components/AuthWrapper";
import { SignInButton } from "@clerk/nextjs";
import { AdaptiveCardRenderer, type ActionPayload } from "@/components/AdaptiveCardRenderer";
import { TypewriterText } from "@/components/TypewriterText";
import { PaymentModal } from "@/components/PaymentModal";
import { PhoneModal } from "@/components/PhoneModal";
import { PreCheckoutModal } from "@/components/PreCheckoutModal";
import { BundleFulfillmentModal } from "@/components/BundleFulfillmentModal";
import { SideNav } from "@/components/SideNav";
import { useSideNavCollapsed } from "@/hooks/useSideNavCollapsed";

type SuggestedCta = { label: string; action: string };

/** Debug trace: prompt sent to model and response received (when Settings → Developer → Prompt trace on) */
export type PromptTrace = {
  request_payload?: { text?: string; messages_count?: number; limit?: number; platform?: string };
  intent?: { request?: { text?: string }; response?: Record<string, unknown> };
  engagement?: { prompt_sent?: string; response_received?: string };
  agent_reasoning?: string[];
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content?: string;
  adaptiveCard?: Record<string, unknown>;
  /** When true, message was loaded from history — skip typewriter effect */
  isFromHistory?: boolean;
  /** When no adaptive card: CTAs to show as buttons (Add to bundle, Proceed to payment) */
  suggestedCtas?: SuggestedCta[];
  /** Context for CTA actions (e.g. first bundle option for add_to_bundle) */
  ctaContext?: {
    suggested_bundle_options?: Array<{ product_ids?: string[]; option_label?: string; [k: string]: unknown }>;
  };
  /** When Settings → Show prompt trace is on: full prompt and response for this turn */
  promptTrace?: PromptTrace;
};

function PromptTraceBlock({ trace }: { trace: PromptTrace; messageId: string }) {
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<"request" | "intent" | "engagement" | "steps">("engagement");
  const req = trace.request_payload;
  const intent = trace.intent;
  const engagement = trace.engagement;
  const steps = trace.agent_reasoning ?? [];
  return (
    <div className="mt-3 w-full rounded-lg border border-[var(--border)] bg-[var(--card)]/50 overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center justify-between px-3 py-2 text-left text-xs font-medium text-[var(--muted)] hover:bg-[var(--border)]/30 transition-colors"
      >
        <span>Prompt trace (request → intent → engagement → steps)</span>
        <span className="text-[var(--muted)]">{expanded ? "▼" : "▶"}</span>
      </button>
      {expanded && (
        <div className="border-t border-[var(--border)] p-3 space-y-3 text-xs">
          <div className="flex gap-2 border-b border-[var(--border)] pb-2 flex-wrap">
            {req && <button type="button" onClick={() => setActiveTab("request")} className={activeTab === "request" ? "font-medium text-[var(--primary-color)]" : "text-[var(--muted)]"}>{`Request`}</button>}
            {intent && <button type="button" onClick={() => setActiveTab("intent")} className={activeTab === "intent" ? "font-medium text-[var(--primary-color)]" : "text-[var(--muted)]"}>{`Intent`}</button>}
            {engagement && <button type="button" onClick={() => setActiveTab("engagement")} className={activeTab === "engagement" ? "font-medium text-[var(--primary-color)]" : "text-[var(--muted)]"}>{`Engagement`}</button>}
            {steps.length > 0 && <button type="button" onClick={() => setActiveTab("steps")} className={activeTab === "steps" ? "font-medium text-[var(--primary-color)]" : "text-[var(--muted)]"}>{`Steps (${steps.length})`}</button>}
          </div>
          {activeTab === "request" && req && (
            <div className="space-y-1">
              <div className="font-medium text-[var(--muted)]">Sent to backend</div>
              <pre className="whitespace-pre-wrap break-words rounded bg-[var(--background)] p-2 max-h-48 overflow-y-auto">{JSON.stringify(req, null, 2)}</pre>
            </div>
          )}
          {activeTab === "intent" && intent && (
            <div className="space-y-2">
              <div>
                <div className="font-medium text-[var(--muted)]">Intent request</div>
                <pre className="whitespace-pre-wrap break-words rounded bg-[var(--background)] p-2 max-h-32 overflow-y-auto">{JSON.stringify(intent.request ?? {}, null, 2)}</pre>
              </div>
              <div>
                <div className="font-medium text-[var(--muted)]">Intent response</div>
                <pre className="whitespace-pre-wrap break-words rounded bg-[var(--background)] p-2 max-h-48 overflow-y-auto">{JSON.stringify(intent.response ?? {}, null, 2)}</pre>
              </div>
            </div>
          )}
          {activeTab === "engagement" && engagement && (
            <div className="space-y-2">
              <div>
                <div className="font-medium text-[var(--muted)]">Prompt sent to model</div>
                <pre className="whitespace-pre-wrap break-words rounded bg-[var(--background)] p-2 max-h-64 overflow-y-auto text-[11px]">{(engagement.prompt_sent ?? "").slice(0, 8000)}{(engagement.prompt_sent?.length ?? 0) > 8000 ? "\n\n… (truncated)" : ""}</pre>
              </div>
              <div>
                <div className="font-medium text-[var(--muted)]">Response received</div>
                <pre className="whitespace-pre-wrap break-words rounded bg-[var(--background)] p-2 max-h-48 overflow-y-auto">{(engagement.response_received ?? "") || "(empty)"}</pre>
              </div>
            </div>
          )}
          {activeTab === "steps" && steps.length > 0 && (
            <div className="space-y-1">
              <div className="font-medium text-[var(--muted)]">Agent flow (planner steps and tool calls)</div>
              <ol className="list-decimal list-inside space-y-1 rounded bg-[var(--background)] p-2 max-h-48 overflow-y-auto">
                {steps.map((s, i) => (
                  <li key={i} className="text-[11px] whitespace-pre-wrap break-words">{s || "(empty)"}</li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const E2E_ACTIONS = ["add_to_bundle", "add_bundle_bulk", "view_bundle", "remove_from_bundle", "replace_in_bundle", "checkout", "complete_checkout"];
const STANDING_INTENT_ACTION = "approve_standing_intent";

const MAX_DISCOVERY_CYCLE = 5;

function extractProductContainersFromCard(card: Record<string, unknown> | null): unknown[] {
  if (!card || typeof card !== "object") return [];
  const body = (card as Record<string, unknown>).body;
  if (!Array.isArray(body)) return [];
  const containers = body.filter((item) => {
    const c = item as Record<string, unknown>;
    return c?.type === "Container" && c?.style === "emphasis" && Array.isArray(c.items);
  });
  return containers.slice(0, MAX_DISCOVERY_CYCLE);
}

type ProductInfo = { name: string; price: string; product_id: string; product_name?: string };

function extractProductInfoFromContainer(container: unknown): ProductInfo | null {
  if (!container || typeof container !== "object") return null;
  const c = container as Record<string, unknown>;
  const items = c.items as unknown[] | undefined;
  if (!Array.isArray(items)) return null;
  let name = "Unknown";
  let price = "";
  let product_id = "";
  let product_name: string | undefined;
  for (const item of items) {
    if (!item || typeof item !== "object") continue;
    const i = item as Record<string, unknown>;
    if (i.type === "TextBlock") {
      const t = String(i.text ?? "");
      if (i.weight === "Bolder" && !t.match(/^\$|^\d|USD|EUR/)) name = t;
      else if (t.match(/USD|EUR|\d+\.\d{2}/)) price = t;
    }
    if (i.type === "ActionSet" && Array.isArray(i.actions)) {
      for (const a of i.actions as Record<string, unknown>[]) {
        const d = a?.data as Record<string, unknown> | undefined;
        if (d?.product_id) {
          product_id = String(d.product_id);
          product_name = d.product_name as string | undefined;
          break;
        }
      }
    }
  }
  return product_id ? { name, price, product_id, product_name } : null;
}

function getHeaderTextFromCard(card: Record<string, unknown> | null): string {
  if (!card || typeof card !== "object") return "";
  const body = (card as Record<string, unknown>).body as unknown[] | undefined;
  if (!Array.isArray(body)) return "";
  for (const item of body) {
    if (item && typeof item === "object") {
      const i = item as Record<string, unknown>;
      if (i.type === "TextBlock" && i.style !== "emphasis") {
        const t = String(i.text ?? "");
        if (t.startsWith("Found ") && t.includes("product")) return t;
      }
    }
  }
  return "";
}

function extractFirstProductFromCard(card: Record<string, unknown> | null): { product_id: string; product_name?: string } | null {
  if (!card || typeof card !== "object") return null;
  const checkActions = (actions: unknown[]): { product_id: string; product_name?: string } | null => {
    for (const a of actions) {
      const d = (a as Record<string, unknown>)?.data as Record<string, unknown> | undefined;
      const pid = d?.product_id;
      if (pid && typeof pid === "string") {
        return { product_id: pid, product_name: d.product_name as string | undefined };
      }
    }
    return null;
  };
  const walk = (obj: unknown): { product_id: string; product_name?: string } | null => {
    if (!obj || typeof obj !== "object") return null;
    const o = obj as Record<string, unknown>;
    const actions = o.actions;
    if (Array.isArray(actions)) {
      const found = checkActions(actions);
      if (found) return found;
    }
    for (const key of ["body", "items"] as const) {
      const arr = o[key];
      if (Array.isArray(arr)) {
        for (const item of arr) {
          const found = walk(item);
          if (found) return found;
        }
      }
    }
    return null;
  };
  return walk(card);
}

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

function getOrCreateAnonymousId(): string {
  if (typeof window === "undefined") return `anon-${Date.now()}`;
  const a = localStorage.getItem(STORAGE_KEY_ANONYMOUS);
  if (a) return a;
  const newA =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `anon-${Date.now()}`;
  localStorage.setItem(STORAGE_KEY_ANONYMOUS, newA);
  return newA;
}

function useThreadPersistence() {
  const [threadId, setThreadIdState] = useState<string | null>(() =>
    typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY_THREAD) : null
  );
  const [anonymousId, setAnonymousIdState] = useState<string | null>(() =>
    typeof window !== "undefined" ? getOrCreateAnonymousId() : null
  );
  const [bundleId, setBundleIdState] = useState<string | null>(() =>
    typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY_BUNDLE) : null
  );
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const t = localStorage.getItem(STORAGE_KEY_THREAD);
    const a = getOrCreateAnonymousId();
    const b = localStorage.getItem(STORAGE_KEY_BUNDLE);
    if (t) setThreadIdState(t);
    setAnonymousIdState(a);
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
  /** Chat display config: typing effect, font size, thinking UI */
  chatConfig?: {
    chat_typing_enabled?: boolean;
    chat_typing_speed_ms?: number;
    font_size_px?: number;
    thinking_ui?: {
      font_size_px?: number;
      color?: string;
      animation_type?: string;
      animation_speed_ms?: number;
    };
    thinking_messages?: Record<string, string>;
  };
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
  /** Thread ID from return URL; used to restore thread if localStorage was cleared */
  paymentSuccessThreadId?: string;
  /** Called after payment success message is shown. Parent should clear URL params. */
  onPaymentSuccessHandled?: () => void;
};

export function ChatPage(props: ChatPageProps = {}) {
  const {
    partnerId,
    e2eEnabled: e2eProp,
    welcomeMessage,
    chatConfig,
    promptToSend,
    onPromptSent,
    embeddedInLanding,
    showSideNav: showSideNavProp,
    paymentSuccessOrderId,
    paymentSuccessThreadId,
    onPaymentSuccessHandled,
  } = props;
  const typingEnabled = chatConfig?.chat_typing_enabled !== false;
  const typingSpeedMs = Math.max(10, Math.min(200, chatConfig?.chat_typing_speed_ms ?? 30));
  const fontSizePx = Math.max(12, Math.min(24, chatConfig?.font_size_px ?? 14));
  const thinkingUi = chatConfig?.thinking_ui ?? {};
  const thinkingFontSizePx = Math.max(12, Math.min(24, thinkingUi.font_size_px ?? 14));
  const thinkingColor = thinkingUi.color ?? "#94a3b8";
  const thinkingAnimation = thinkingUi.animation_type ?? "dots";
  const thinkingSpeedMs = Math.max(200, Math.min(3000, thinkingUi.animation_speed_ms ?? 1000));
  const showSideNav = showSideNavProp ?? !embeddedInLanding;
  const { collapsed: sideNavCollapsed, toggle: toggleSideNav } = useSideNavCollapsed();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pendingApprovals, setPendingApprovals] = useState<
    Array<{ id: string; intent_description: string }>
  >([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [thinkingText, setThinkingText] = useState<string | null>(null);
  const [paymentOrderId, setPaymentOrderId] = useState<string | null>(null);
  const [pendingPhoneOrderId, setPendingPhoneOrderId] = useState<string | null>(null);
  const [preCheckoutOrderId, setPreCheckoutOrderId] = useState<string | null>(null);
  const [fulfillmentModalData, setFulfillmentModalData] = useState<{
    product_ids: string[];
    option_label?: string;
    required_fields: string[];
    initial_values: Record<string, string>;
  } | null>(null);
  const [showPostCheckoutSignInBanner, setShowPostCheckoutSignInBanner] = useState(false);
  const [feedbackByMessage, setFeedbackByMessage] = useState<Record<string, "like" | "dislike">>({});
  const [latestOrder, setLatestOrder] = useState<{
    id: string;
    status: string;
    payment_status: string;
    total_amount: number;
    currency: string;
    created_at: string;
    items?: Array<{ item_name: string; quantity: number; total_price: number }>;
  } | null>(null);
  const e2eEnabled = e2eProp ?? true;
  const sessionId = useSessionId();
  const { isSignedIn } = useAuthState();
  const [userId, setUserId] = useState<string | null>(null);
  const [promptTraceEnabled, setPromptTraceEnabled] = useState(false);
  useEffect(() => {
    const read = () => {
      try {
        setPromptTraceEnabled(typeof window !== "undefined" && localStorage.getItem("chat_debug_show_prompt_trace") === "true");
      } catch {
        setPromptTraceEnabled(false);
      }
    };
    read();
    window.addEventListener("storage", read);
    window.addEventListener("focus", read);
    return () => {
      window.removeEventListener("storage", read);
      window.removeEventListener("focus", read);
    };
  }, []);

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

  useEffect(() => {
    if (hydrated && paymentSuccessThreadId && !threadId) {
      setThreadId(paymentSuccessThreadId);
    }
  }, [hydrated, paymentSuccessThreadId, threadId, setThreadId]);

  const prevLoadedThreadIdRef = useRef<string | null>(null);
  const paymentSuccessHandledRef = useRef(false);
  const [threads, setThreads] = useState<Array<{ id: string; title: string; updated_at: string; has_completed_order?: boolean }>>([]);
  const fetchThreads = useCallback(() => {
    const aid = userId ? null : (anonymousId ?? (typeof window !== "undefined" ? getOrCreateAnonymousId() : null));
    const url = userId ? "/api/threads" : aid ? `/api/threads?anonymous_id=${encodeURIComponent(aid)}` : null;
    if (!url) return;
    fetch(url)
      .then((r) => r.json())
      .then((d) => setThreads(d.threads ?? []))
      .catch(() => setThreads([]));
  }, [userId, anonymousId]);
  useEffect(() => {
    if (userId) fetchThreads();
    else if (anonymousId || (typeof window !== "undefined" && getOrCreateAnonymousId())) fetchThreads();
  }, [userId, anonymousId, fetchThreads]);

  useEffect(() => {
    if (userId) setShowPostCheckoutSignInBanner(false);
  }, [userId]);

  const handleSelectThread = useCallback(
    (id: string | null) => {
      prevLoadedThreadIdRef.current = null;
      setThreadId(id);
      setMessages([]);
      setPendingApprovals([]);
      setLatestOrder(null);
      if (!id) setBundleId(null);
      fetchThreads(); // Refresh list so previous conversation appears when switching to new chat
    },
    [setThreadId, setBundleId, fetchThreads]
  );

  const handleDeleteThread = useCallback(
    async (id: string) => {
      const params = userId
        ? ""
        : anonymousId
          ? `?anonymous_id=${encodeURIComponent(anonymousId)}`
          : "";
      const res = await fetch(`/api/threads/${id}${params}`, { method: "DELETE" });
      const d = await res.json();
      if (!res.ok) {
        alert(d.message || d.error || "Failed to delete");
        return;
      }
      if (threadId === id) handleSelectThread(null);
      fetchThreads();
    },
    [userId, anonymousId, threadId, handleSelectThread, fetchThreads]
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

  const persistMessage = useCallback(
    (msg: { role: "user" | "assistant"; content?: string; adaptiveCard?: Record<string, unknown> }) => {
      if (!threadId) return;
      const authParam = userId
        ? { user_id: userId }
        : anonymousId
          ? { anonymous_id: anonymousId }
          : null;
      if (!authParam) return;
      fetch(`/api/threads/${threadId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [
            {
              role: msg.role,
              content: msg.content ?? null,
              adaptive_card: msg.adaptiveCard ?? null,
            },
          ],
          ...authParam,
        }),
      }).catch(() => {});
    },
    [threadId, userId, anonymousId]
  );

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
            isFromHistory: true,
          })
        );
        if (paymentSuccessOrderId && !paymentSuccessHandledRef.current) {
          const confirmMsg = { role: "assistant" as const, content: "Payment confirmed! Thank you for your order." };
          msgs.push({
            ...confirmMsg,
            id: `msg-${Date.now()}-${Math.random().toString(36).slice(2)}`,
          });
          paymentSuccessHandledRef.current = true;
          persistMessage(confirmMsg);
          if (!isSignedIn) setShowPostCheckoutSignInBanner(true);
          onPaymentSuccessHandled?.();
        }
        setMessages(msgs);
        if (data.thread?.bundle_id) setBundleId(data.thread.bundle_id);
        setPendingApprovals(data.pending_approvals ?? []);
        setLatestOrder(data.thread?.latest_order ?? null);
      })
      .catch(() => {});
  }, [hydrated, threadId, anonymousId, userId, setBundleId, paymentSuccessOrderId, persistMessage, isSignedIn, onPaymentSuccessHandled]);

  // Save conversation when user signs in (link anonymous thread to user)
  useEffect(() => {
    if (!isSignedIn || !threadId || !anonymousId) return;
    fetch(`/api/threads/${threadId}/link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ anonymous_id: anonymousId }),
    }).catch(() => {});
  }, [isSignedIn, threadId, anonymousId]);

  // When user signs in from PreCheckoutModal: check order phone, proceed to payment
  useEffect(() => {
    if (!preCheckoutOrderId || !isSignedIn) return;
    const orderId = preCheckoutOrderId;
    setPreCheckoutOrderId(null);
    fetch(`/api/orders/${orderId}`)
      .then((r) => r.json())
      .then((data) => {
        const hasPhone = !!data?.customer_phone;
        if (hasPhone) {
          if (STRIPE_CONFIGURED) {
            setPaymentOrderId(orderId);
          } else {
            setLoading(true);
            fetch("/api/payment/confirm", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ order_id: orderId }),
            })
              .then((r) => r.json())
              .then((json) => {
                if (!json.error) {
                  const addMsg = { role: "assistant" as const, content: json.message || "Payment confirmed! Thank you for your order." };
                  addMessage(addMsg);
                  persistMessage(addMsg);
                } else {
                  addMessage({ role: "assistant", content: json.error || "Payment failed." });
                }
              })
              .catch(() => addMessage({ role: "assistant", content: "Payment failed." }))
              .finally(() => setLoading(false));
          }
        } else {
          setPendingPhoneOrderId(orderId);
        }
      })
      .catch(() => setPendingPhoneOrderId(orderId));
  }, [preCheckoutOrderId, isSignedIn, addMessage, persistMessage]);

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
        const effectiveAnonymousId = anonymousId ?? (typeof window !== "undefined" ? getOrCreateAnonymousId() : undefined);
        if (threadId) {
          payload.thread_id = threadId;
          if (userId) payload.user_id = userId;
          else payload.anonymous_id = effectiveAnonymousId;
        } else if (userId) {
          payload.user_id = userId;
        } else if (effectiveAnonymousId) {
          payload.anonymous_id = effectiveAnonymousId;
        } else {
          payload.user_id = sessionId;
        }
        if (bundleId) payload.bundle_id = bundleId;
        if (latestOrder?.id) payload.order_id = latestOrder.id;
        payload.stream = true;
        if (promptTraceEnabled || (typeof window !== "undefined" && localStorage.getItem("chat_debug_show_prompt_trace") === "true")) {
          payload.debug = true;
        }

        setThinkingText(null);
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        type ChatResponse = {
          data?: {
            products?: { products?: Array<{ name?: string; price?: number }>; count?: number };
            engagement?: { suggested_bundle_options?: Array<{ product_ids?: string[]; option_label?: string; [k: string]: unknown }> };
            text?: string;
            error?: string;
          };
          summary?: string;
          message?: string;
          error?: string;
          adaptive_card?: Record<string, unknown>;
          suggested_ctas?: SuggestedCta[];
          prompt_trace?: PromptTrace;
        };

        const contentType = res.headers.get("content-type") || "";
        if (contentType.includes("text/event-stream") && res.body) {
          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          let data: ChatResponse = {};
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop() || "";
            for (const block of lines) {
              let eventType = "";
              let eventData = "";
              for (const line of block.split("\n")) {
                if (line.startsWith("event: ")) eventType = line.slice(7).trim();
                else if (line.startsWith("data: ")) eventData = line.slice(6);
              }
              if (eventType === "thinking" && eventData) {
                try {
                  const parsed = JSON.parse(eventData) as { text?: string };
                  setThinkingText(parsed.text || "Thinking...");
                } catch {
                  setThinkingText(eventData || "Thinking...");
                }
              } else if (eventType === "done" && eventData) {
                try {
                  data = JSON.parse(eventData) as ChatResponse;
                } catch {
                  /* ignore */
                }
              } else if (eventType === "error" && eventData) {
                try {
                  const err = JSON.parse(eventData) as { error?: string };
                  throw new Error(err.error || "Stream error");
                } catch (e) {
                  if (e instanceof Error) throw e;
                  throw new Error("Stream error");
                }
              }
            }
          }
          if (!res.ok) {
            const errMsg = (data as { error?: string }).error || `HTTP ${res.status}`;
            throw new Error(errMsg);
          }
          const productList = data.data?.products?.products ?? [];
          let assistantContent =
            data.summary ??
            (productList.length > 0
              ? `Found ${productList.length} products`
              : data.data?.text ?? data.message ?? "");
          if (!assistantContent || assistantContent === "{}") {
            assistantContent = "I'm here to help. What would you like to explore—gifts, flowers, experiences, or something else?";
          }
          const newThreadId = (data as { thread_id?: string }).thread_id;
          const threadTitle = (data as { thread_title?: string }).thread_title;
          if (newThreadId && !threadId) {
            setThreadId(newThreadId);
            setThreads((prev) => {
              if (prev.some((t) => t.id === newThreadId)) return prev;
              return [
                {
                  id: newThreadId,
                  title: threadTitle || userMessage.slice(0, 50) || "New chat",
                  updated_at: new Date().toISOString(),
                },
                ...prev,
              ];
            });
          }
          fetchThreads();
          const suggestedCtas = Array.isArray((data as ChatResponse).suggested_ctas) ? (data as ChatResponse).suggested_ctas : undefined;
          const opts = (data as ChatResponse).data?.engagement?.suggested_bundle_options;
          const promptTrace = (data as ChatResponse).prompt_trace;
          addMessage({
            role: "assistant",
            content: assistantContent,
            adaptiveCard: data.adaptive_card,
            ...(suggestedCtas?.length && { suggestedCtas }),
            ...(suggestedCtas?.length && opts?.length && { ctaContext: { suggested_bundle_options: opts } }),
            ...(promptTrace && { promptTrace }),
          });
        } else {
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
          let assistantContent =
            data.summary ??
            (productList.length > 0
              ? `Found ${productList.length} products`
              : data.data?.text ?? data.message ?? "");
          if (!assistantContent || assistantContent === "{}") {
            assistantContent = "I'm here to help. What would you like to explore—gifts, flowers, experiences, or something else?";
          }
          const newThreadId = (data as { thread_id?: string }).thread_id;
          const threadTitle = (data as { thread_title?: string }).thread_title;
          if (newThreadId && !threadId) {
            setThreadId(newThreadId);
            setThreads((prev) => {
              if (prev.some((t) => t.id === newThreadId)) return prev;
              return [
                {
                  id: newThreadId,
                  title: threadTitle || userMessage.slice(0, 50) || "New chat",
                  updated_at: new Date().toISOString(),
                },
                ...prev,
              ];
            });
          }
          fetchThreads();
          const suggestedCtas = Array.isArray(data.suggested_ctas) ? data.suggested_ctas : undefined;
          const opts = data.data?.engagement?.suggested_bundle_options;
          const promptTraceNonStream = data.prompt_trace;
          addMessage({
            role: "assistant",
            content: assistantContent,
            adaptiveCard: data.adaptive_card,
            ...(suggestedCtas?.length && { suggestedCtas }),
            ...(suggestedCtas?.length && opts?.length && { ctaContext: { suggested_bundle_options: opts } }),
            ...(promptTraceNonStream && { promptTrace: promptTraceNonStream }),
          });
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        addMessage({ role: "assistant", content: `Error: ${msg}` });
      } finally {
        setThinkingText(null);
        setLoading(false);
        if (fromPrompt) onPromptSent?.();
      }
    },
    [addMessage, loading, messages, partnerId, sessionId, threadId, anonymousId, setThreadId, onPromptSent, userId, fetchThreads, bundleId, latestOrder, promptTraceEnabled]
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
    if (!paymentSuccessOrderId || !hydrated || paymentSuccessHandledRef.current) return;
    if (threadId && (userId || anonymousId)) return;
    const content = "Payment confirmed! Thank you for your order.";
    addMessage({ role: "assistant", content });
    if (!isSignedIn) setShowPostCheckoutSignInBanner(true);
    paymentSuccessHandledRef.current = true;
    onPaymentSuccessHandled?.();
  }, [paymentSuccessOrderId, hydrated, threadId, userId, anonymousId, addMessage, onPaymentSuccessHandled, isSignedIn]);

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
          const content =
              json.approved !== false
                ? "Standing intent approved. We'll notify you when it's ready."
                : "Standing intent rejected.";
          addMessage({ role: "assistant", content });
          persistMessage({ role: "assistant", content });
        } catch (err) {
          const content = `Error: ${err instanceof Error ? err.message : String(err)}`;
          addMessage({ role: "assistant", content });
          persistMessage({ role: "assistant", content });
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

          const addMsg = { role: "assistant" as const, content: json.summary || "Added to bundle.", adaptiveCard: json.adaptive_card };
          addMessage(addMsg);
          persistMessage(addMsg);
          if (json.adaptive_card) return;
        }

        if (action === "add_bundle_bulk" && data.product_ids && Array.isArray(data.product_ids)) {
          const requiresFulfillment = data.requires_fulfillment === true;
          const requiredFields: string[] = Array.isArray(data.fulfillment_fields)
            ? data.fulfillment_fields
            : ["pickup_time", "pickup_address", "delivery_address"];
          const initialValues: Record<string, string> = {};
          for (const f of requiredFields) {
            const v = (data[f] as string)?.trim?.() || "";
            initialValues[f] = v;
          }
          const hasAllFulfillment = requiredFields.every((f) => (initialValues[f] ?? "").trim().length > 0);

          if (requiresFulfillment && hasAllFulfillment) {
            // User already provided address/time in conversation — skip modal, add directly
            const addPayload: Record<string, unknown> = {
              product_ids: data.product_ids,
              requires_fulfillment: true,
              fulfillment_fields: requiredFields,
              ...Object.fromEntries(requiredFields.map((f) => [f, initialValues[f]])),
            };
            if (bundleId) addPayload.bundle_id = bundleId;

            const res = await fetch("/api/bundle/add-bulk", {
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

            const addMsg = { role: "assistant" as const, content: json.summary || "Added to bundle.", adaptiveCard: json.adaptive_card };
            addMessage(addMsg);
            persistMessage(addMsg);
            if (json.adaptive_card) return;
          } else if (requiresFulfillment) {
            setFulfillmentModalData({
              product_ids: data.product_ids,
              option_label: data.option_label as string | undefined,
              required_fields: requiredFields,
              initial_values: initialValues,
            });
            setLoading(false);
            return;
          }

          const addPayload: Record<string, unknown> = {
            product_ids: data.product_ids,
          };
          if (bundleId) addPayload.bundle_id = bundleId;

          const res = await fetch("/api/bundle/add-bulk", {
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

          const addMsg = { role: "assistant" as const, content: json.summary || "Added to bundle.", adaptiveCard: json.adaptive_card };
          addMessage(addMsg);
          persistMessage(addMsg);
          if (json.adaptive_card) return;
        }

        if (action === "view_bundle" && data.bundle_id) {
          const res = await fetch(`/api/bundles/${data.bundle_id}`);
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Bundle not found");
          const addMsg = { role: "assistant" as const, content: json.summary, adaptiveCard: json.adaptive_card };
          addMessage(addMsg);
          persistMessage(addMsg);
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
          const addMsg = { role: "assistant" as const, content: json.summary || "Item removed." };
          addMessage(addMsg);
          persistMessage(addMsg);
          return;
        }

        if (action === "replace_in_bundle" && data.bundle_id && data.leg_id && data.product_id) {
          const res = await fetch("/api/bundle/replace", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              bundle_id: data.bundle_id,
              leg_id: data.leg_id,
              new_product_id: data.product_id,
            }),
          });
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Replace failed");
          const addMsg = {
            role: "assistant" as const,
            content: json.summary || "Replaced. Bundle updated.",
            adaptiveCard: json.adaptive_card,
          };
          addMessage(addMsg);
          persistMessage(addMsg);
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
          const orderId = json.order_id ?? json.data?.order_id;
          if (orderId) {
            setLatestOrder({
              id: orderId,
              status: "pending",
              payment_status: "pending",
              created_at: new Date().toISOString(),
              currency: (json.data?.currency as string) ?? "USD",
              total_amount: typeof json.data?.total_amount === "number" ? json.data.total_amount : 0,
              items: Array.isArray(json.data?.items) ? json.data.items : [],
            });
          }
          const addMsg = { role: "assistant" as const, content: json.summary, adaptiveCard: json.adaptive_card };
          addMessage(addMsg);
          persistMessage(addMsg);
          return;
        }

        if (action === "complete_checkout" && data.order_id) {
          const orderId = data.order_id;
          if (userId) {
            // Signed-in user: check if phone needed, then proceed
            const orderRes = await fetch(`/api/orders/${orderId}`);
            const orderData = await orderRes.json().catch(() => ({}));
            const hasPhone = !!orderData?.customer_phone;
            if (!hasPhone) {
              setPendingPhoneOrderId(orderId);
              return;
            }
            if (STRIPE_CONFIGURED) {
              setPaymentOrderId(orderId);
              return;
            }
            const res = await fetch("/api/payment/confirm", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ order_id: orderId }),
            });
            const json = await res.json();
            if (!res.ok) throw new Error(json.error || "Payment failed");
            const addMsg = { role: "assistant" as const, content: json.message || "Payment confirmed! Thank you for your order." };
            addMessage(addMsg);
            persistMessage(addMsg);
            return;
          }
          // Anonymous user: show sign-in before checkout (or phone if no Clerk)
          if (hasClerk) {
            setPreCheckoutOrderId(orderId);
          } else {
            setPendingPhoneOrderId(orderId);
          }
          return;
        }

        if (action === "edit_order") {
          const bid = data.bundle_id || bundleId;
          if (bid) {
            const res = await fetch(`/api/bundles/${bid}`);
            const json = await res.json();
            if (!res.ok) throw new Error(json.error || "Bundle not found");
            const addMsg = { role: "assistant" as const, content: json.summary, adaptiveCard: json.adaptive_card };
            addMessage(addMsg);
            persistMessage(addMsg);
            setBundleId(bid);
            return;
          }
          const addMsg = { role: "assistant" as const, content: "What would you like to change? You can add more items or remove items from your bundle." };
          addMessage(addMsg);
          persistMessage(addMsg);
          return;
        }

        if (action === "add_more") {
          const addMsg = { role: "assistant" as const, content: "What else would you like to add? Try searching for more products." };
          addMessage(addMsg);
          persistMessage(addMsg);
          return;
        }

        if (action === "view_details" && data.product_id) {
          const res = await fetch(`/api/products/${data.product_id}`);
          const json = await res.json();
          if (!res.ok) throw new Error(json.error || "Product not found");
          const addMsg = { role: "assistant" as const, content: `${json.data?.name || "Product"} — ${json.data?.currency || "USD"} ${Number(json.data?.price || 0).toFixed(2)}` };
          addMessage(addMsg);
          persistMessage(addMsg);
          return;
        }

        if (action === "add_to_favorites" && data.product_id) {
          if (!isSignedIn) {
            const addMsg = { role: "assistant" as const, content: "Sign in to save favorites — your favorites will sync across devices." };
            addMessage(addMsg);
            persistMessage(addMsg);
            setShowPostCheckoutSignInBanner(true);
            return;
          }
          const favPayload: Record<string, string> = {
            item_type: "product",
            item_id: data.product_id,
            item_name: typeof data.product_name === "string" ? data.product_name : "",
          };
          const res = await fetch("/api/my-stuff/favorites", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(favPayload),
            credentials: "include",
          });
          const text = await res.text();
          let json: { error?: string } = {};
          try {
            json = text ? (JSON.parse(text) as { error?: string }) : {};
          } catch {
            json = { error: "Invalid response" };
          }
          if (!res.ok) {
            if (res.status === 401 && json.error?.toLowerCase().includes("sign in")) {
              const addMsg = { role: "assistant" as const, content: "Sign in to save favorites — your favorites will sync across devices." };
              addMessage(addMsg);
              persistMessage(addMsg);
              setShowPostCheckoutSignInBanner(true);
              return;
            }
            if (res.status === 503) {
              const addMsg = { role: "assistant" as const, content: "Unable to save favorites right now. Please try again in a moment." };
              addMessage(addMsg);
              persistMessage(addMsg);
              return;
            }
            throw new Error(json.error || "Failed to save");
          }
          const addMsg = { role: "assistant" as const, content: "Saved to My Stuff!" };
          addMessage(addMsg);
          persistMessage(addMsg);
          window.dispatchEvent(new Event("my-stuff-refresh"));
          return;
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        const isSignInError = msg.toLowerCase().includes("sign in") && msg.toLowerCase().includes("favorite");
        const content = isSignInError
          ? "Sign in to save favorites — your favorites will sync across devices."
          : `Error: ${msg}`;
        addMessage({ role: "assistant", content });
        persistMessage({ role: "assistant", content });
        if (isSignInError) setShowPostCheckoutSignInBanner(true);
      } finally {
        setLoading(false);
      }
    },
    [addMessage, persistMessage, e2eEnabled, sessionId, setPaymentOrderId, threadId, anonymousId, bundleId, setBundleId, setPendingApprovals, userId, isSignedIn, setShowPostCheckoutSignInBanner, setPendingPhoneOrderId, setPreCheckoutOrderId, setFulfillmentModalData]
  );

  const handleFulfillmentSubmit = useCallback(
    async (details: Record<string, string>) => {
      if (!fulfillmentModalData) return;
      setLoading(true);
      setFulfillmentModalData(null);
      try {
        const addPayload: Record<string, unknown> = {
          product_ids: fulfillmentModalData.product_ids,
          requires_fulfillment: true,
          fulfillment_fields: fulfillmentModalData.required_fields,
          ...details,
        };
        if (bundleId) addPayload.bundle_id = bundleId;

        const res = await fetch("/api/bundle/add-bulk", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(addPayload),
        });
        const json = await res.json();
        if (!res.ok) {
          const errMsg = typeof json.detail === "object" && json.detail?.message
            ? json.detail.message
            : typeof json.detail === "string"
              ? json.detail
              : json.error || "Add to bundle failed";
          throw new Error(errMsg);
        }

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

        const addMsg = { role: "assistant" as const, content: json.summary || "Added to bundle.", adaptiveCard: json.adaptive_card };
        addMessage(addMsg);
        persistMessage(addMsg);
      } catch (err) {
        const content = `Error: ${err instanceof Error ? err.message : String(err)}`;
        addMessage({ role: "assistant", content });
        persistMessage({ role: "assistant", content });
      } finally {
        setLoading(false);
      }
    },
    [fulfillmentModalData, bundleId, threadId, userId, anonymousId, setBundleId, addMessage, persistMessage]
  );

  const submitFeedback = useCallback(
    async (messageId: string, rating: "like" | "dislike", productIds?: string[]) => {
      if (!threadId) return;
      setFeedbackByMessage((prev) => ({ ...prev, [messageId]: rating }));
      const payload: Record<string, unknown> = {
        thread_id: threadId,
        rating,
        context: productIds?.length ? { product_ids: productIds } : {},
      };
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      if (uuidRegex.test(messageId)) payload.message_id = messageId;
      if (!userId && anonymousId) payload.anonymous_id = anonymousId;
      try {
        const res = await fetch("/api/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          console.warn("Feedback failed:", data.error);
          setFeedbackByMessage((prev) => {
            const next = { ...prev };
            delete next[messageId];
            return next;
          });
        }
      } catch (err) {
        console.warn("Feedback failed:", err);
        setFeedbackByMessage((prev) => {
          const next = { ...prev };
          delete next[messageId];
          return next;
        });
      }
    },
    [threadId, userId, anonymousId]
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    sendMessage(input.trim(), false);
  }

  const chatContent = (
    <div className={`flex flex-col bg-[var(--background)] text-[var(--foreground)] ${showSideNav ? "min-h-0 flex-1 overflow-hidden" : embeddedInLanding ? "min-h-[60vh]" : "h-screen"}`}>
      <main
        className={`h-0 min-h-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-y-contain px-4 py-6 ${embeddedInLanding ? "border border-[var(--border)] rounded-xl" : ""} ${messages.length === 0 ? "flex flex-col justify-center" : ""}`}
      >
        <div className={`mx-auto min-w-0 w-full max-w-3xl space-y-6 ${messages.length === 0 ? "flex flex-col items-center" : ""}`}>
          {embeddedInLanding && (userId || anonymousId) && (
            <div className="flex justify-end">
              <select
                value={threadId ?? ""}
                onChange={(e) => handleSelectThread(e.target.value || null)}
                className="text-sm px-2 py-1.5 rounded border border-[var(--border)] bg-[var(--card)]"
                title="Switch conversation"
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
          {latestOrder && (
            <div className="w-full max-w-3xl mx-auto mb-4">
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div>
                    <p className="font-medium text-emerald-400">
                      Order #{latestOrder.id.slice(0, 8)}… • {latestOrder.status}
                    </p>
                    <p className="text-sm text-slate-400 mt-0.5">
                      {latestOrder.currency} {latestOrder.total_amount.toFixed(2)} • Paid
                    </p>
                    {latestOrder.items && latestOrder.items.length > 0 && (
                      <p className="text-xs text-slate-500 mt-1">
                        {latestOrder.items.map((i) => `${i.item_name} × ${i.quantity}`).join(", ")}
                      </p>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">
                    Continue chatting below for order updates or support.
                  </p>
                </div>
              </div>
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
                className={`flex min-w-0 w-full ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div className="flex min-w-0 w-full flex-col gap-1">
                  <div
                    className={`min-w-0 rounded-2xl px-4 py-3 ${
                      m.role === "user"
                        ? "max-w-[85%] self-end bg-[var(--primary-color)] text-[var(--primary-foreground)]"
                        : "w-full max-w-full bg-[var(--card)] text-[var(--card-foreground)]"
                    }`}
                  >
                    {m.content && (
                      <div className="chat-markdown" style={{ fontSize: `${fontSizePx}px` }}>
                        {m.role === "assistant" && typingEnabled && !m.isFromHistory ? (
                          <TypewriterText
                            text={m.content}
                            speedMs={typingSpeedMs}
                            enabled={typingEnabled}
                            render={(displayed) => <ReactMarkdown>{displayed}</ReactMarkdown>}
                          />
                        ) : (
                          <ReactMarkdown>{m.content}</ReactMarkdown>
                        )}
                      </div>
                    )}
                    {/* Adaptive card: product/bundle UI when orchestrator returns one */}
                    {m.adaptiveCard && (() => {
                      const card = m.adaptiveCard as Record<string, unknown>;
                      const rawCard = filterE2EActions(card, e2eEnabled);
                      const productContainers = extractProductContainersFromCard(rawCard);
                      const products = productContainers
                        .map((c) => extractProductInfoFromContainer(c))
                        .filter((p): p is ProductInfo => p !== null);
                      const header = getHeaderTextFromCard(rawCard) || (products.length > 0 ? `Found ${products.length} product(s)` : "");
                      if (products.length > 0) {
                        return (
                          <div className="mt-3 w-full min-w-0 space-y-3 text-sm" style={{ fontSize: `${fontSizePx}px` }}>
                            <p className="font-medium">{header}</p>
                            {products.map((p, idx) => (
                              <div key={p.product_id} className="rounded-lg bg-[var(--card)]/60 px-3 py-2 border border-[var(--border)]/50">
                                <p className="text-[rgb(var(--color-text-secondary))] text-xs mb-1">
                                  Option {idx + 1} of {products.length}
                                </p>
                                <p className="font-medium">{p.name}</p>
                                {p.price && <p className="text-sm text-[rgb(var(--color-text-secondary))]">{p.price}</p>}
                                <div className="mt-2 flex gap-2 flex-wrap">
                                  <button
                                    type="button"
                                    onClick={() => handleAction({ action: "add_to_bundle", product_id: p.product_id })}
                                    className="text-xs px-2 py-1 rounded bg-[var(--primary-color)]/20 text-[var(--primary-color)] hover:bg-[var(--primary-color)]/30 transition-colors"
                                  >
                                    Add to Bundle
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleAction({ action: "view_details", product_id: p.product_id })}
                                    className="text-xs px-2 py-1 rounded border border-[var(--border)] text-[rgb(var(--color-text-secondary))] hover:bg-[var(--border)]/30 transition-colors"
                                  >
                                    Details
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleAction({ action: "add_to_favorites", product_id: p.product_id, product_name: p.product_name || p.name })}
                                    className="text-xs px-2 py-1 rounded border border-[var(--border)] text-[rgb(var(--color-text-secondary))] hover:bg-[var(--border)]/30 transition-colors"
                                  >
                                    Favorite
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        );
                      }
                      return (
                        <div className="mt-3 w-full min-w-0">
                          <AdaptiveCardRenderer card={rawCard} onAction={handleAction} className="w-full" />
                        </div>
                      );
                    })()}
                    {/* When no adaptive card: render suggested_ctas as buttons (Add to bundle, Proceed to payment) */}
                    {m.role === "assistant" && m.suggestedCtas && m.suggestedCtas.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {m.suggestedCtas.map((cta, idx) => (
                          <button
                            key={`${cta.action}-${idx}`}
                            type="button"
                            onClick={() => {
                              if (cta.action === "add_to_bundle") {
                                const first = m.ctaContext?.suggested_bundle_options?.[0];
                                const productIds = first?.product_ids;
                                if (productIds?.length) {
                                  handleAction({ action: "add_bundle_bulk", product_ids: productIds, option_label: first?.option_label });
                                } else if (bundleId) {
                                  handleAction({ action: "view_bundle", bundle_id: bundleId });
                                }
                              } else if (cta.action === "proceed_to_payment" && latestOrder?.id) {
                                handleAction({ action: "complete_checkout", order_id: latestOrder.id });
                              }
                            }}
                            className="px-3 py-1.5 rounded-lg text-sm font-medium bg-[var(--primary-color)] text-[var(--primary-foreground)] hover:opacity-90 transition-opacity"
                          >
                            {cta.label}
                          </button>
                        ))}
                      </div>
                    )}
                    {/* Debug: prompt trace (when Settings → Developer → Prompt trace on) */}
                    {m.role === "assistant" && m.promptTrace && (
                      <PromptTraceBlock trace={m.promptTrace} messageId={m.id} />
                    )}
                    {m.role === "assistant" && promptTraceEnabled && !m.promptTrace && (
                      <div className="mt-3 rounded-lg border border-dashed border-[var(--border)] bg-[var(--card)]/30 px-3 py-2 text-xs text-[var(--muted)]">
                        Prompt trace is on. Send a <strong>new message</strong> to see &quot;Prompt trace (request → intent → engagement → steps)&quot; under the next reply. Restart the Orchestrator service if you still don&apos;t see it.
                      </div>
                    )}
                  </div>
                  {m.role === "assistant" && (
                    <div className="flex items-center gap-1 pl-1 flex-wrap">
                      {e2eEnabled && (() => {
                        const product = extractFirstProductFromCard(m.adaptiveCard ?? null);
                        const hasProduct = !!product?.product_id;
                        const hasBundle = !!bundleId;
                        return (
                          <>
                            {hasProduct && (
                              <>
                                <button
                                  type="button"
                                  aria-label="Add to favorites"
                                  title="Add to favorites"
                                  onClick={() => handleAction({ action: "add_to_favorites", product_id: product!.product_id, product_name: product!.product_name })}
                                  className="rounded p-1.5 text-slate-400 transition-colors hover:bg-[var(--border)] hover:text-[var(--primary-color)]"
                                >
                                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                                  </svg>
                                </button>
                                <button
                                  type="button"
                                  aria-label="Add to bundle"
                                  title="Add to bundle"
                                  onClick={() => handleAction({ action: "add_to_bundle", product_id: product!.product_id })}
                                  className="rounded p-1.5 text-slate-400 transition-colors hover:bg-[var(--border)] hover:text-[var(--primary-color)]"
                                >
                                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                                  </svg>
                                </button>
                              </>
                            )}
                            {hasBundle && (
                              <>
                                <button
                                  type="button"
                                  aria-label="View bundle"
                                  title="View bundle"
                                  onClick={() => handleAction({ action: "view_bundle", bundle_id: bundleId! })}
                                  className="rounded p-1.5 text-slate-400 transition-colors hover:bg-[var(--border)] hover:text-[var(--primary-color)]"
                                >
                                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                                  </svg>
                                </button>
                                <button
                                  type="button"
                                  aria-label="Checkout"
                                  title="Checkout"
                                  onClick={() => handleAction({ action: "checkout", bundle_id: bundleId! })}
                                  className="rounded p-1.5 text-slate-400 transition-colors hover:bg-[var(--border)] hover:text-[var(--primary-color)]"
                                >
                                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                                  </svg>
                                </button>
                              </>
                            )}
                          </>
                        );
                      })()}
                      <button
                        type="button"
                        aria-label="Like"
                        title="Like this suggestion"
                        onClick={() => {
                          const product = extractFirstProductFromCard(m.adaptiveCard ?? null);
                          submitFeedback(m.id, "like", product?.product_id ? [product.product_id] : undefined);
                        }}
                        className={`rounded p-1.5 transition-colors hover:bg-[var(--border)] ${
                          feedbackByMessage[m.id] === "like"
                            ? "text-[var(--primary-color)]"
                            : "text-slate-400 hover:text-white"
                        }`}
                      >
                        <svg
                          className="h-4 w-4"
                          fill={feedbackByMessage[m.id] === "like" ? "currentColor" : "none"}
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        aria-label="Dislike"
                        title="Dislike this suggestion"
                        onClick={() => {
                          const product = extractFirstProductFromCard(m.adaptiveCard ?? null);
                          submitFeedback(m.id, "dislike", product?.product_id ? [product.product_id] : undefined);
                        }}
                        className={`rounded p-1.5 transition-colors hover:bg-[var(--border)] ${
                          feedbackByMessage[m.id] === "dislike"
                            ? "text-red-400"
                            : "text-slate-400 hover:text-white"
                        }`}
                      >
                        <svg
                          className="h-4 w-4"
                          fill={feedbackByMessage[m.id] === "dislike" ? "currentColor" : "none"}
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        aria-label="Look for more options"
                        title="Look for more options"
                        onClick={() => sendMessage("Show me more options", false)}
                        className="rounded p-1.5 text-slate-400 transition-colors hover:bg-[var(--border)] hover:text-white"
                      >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
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
              <div className="rounded-2xl bg-[var(--card)] px-4 py-3">
                <div className="flex items-center gap-2">
                  {thinkingAnimation === "dots" && (
                    <>
                      <span
                        className="inline-block h-2 w-2 animate-typing-1 rounded-full"
                        style={{ backgroundColor: thinkingColor }}
                      />
                      <span
                        className="inline-block h-2 w-2 animate-typing-2 rounded-full"
                        style={{ backgroundColor: thinkingColor }}
                      />
                      <span
                        className="inline-block h-2 w-2 animate-typing-3 rounded-full"
                        style={{ backgroundColor: thinkingColor }}
                      />
                    </>
                  )}
                  {thinkingAnimation === "pulse" && (
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{
                        backgroundColor: thinkingColor,
                        animation: `thinking-pulse ${thinkingSpeedMs}ms ease-in-out infinite`,
                      }}
                    />
                  )}
                  {thinkingAnimation === "fade" && (
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{
                        backgroundColor: thinkingColor,
                        animation: `thinking-fade ${thinkingSpeedMs}ms ease-in-out infinite`,
                      }}
                    />
                  )}
                  {thinkingAnimation === "none" && (
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ backgroundColor: thinkingColor }}
                    />
                  )}
                  <span
                    className="ml-0.5"
                    style={{ fontSize: thinkingFontSizePx, color: thinkingColor }}
                  >
                    {thinkingText ?? "Thinking..."}
                  </span>
                </div>
              </div>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      {preCheckoutOrderId && hasClerk && (
        <PreCheckoutModal
          orderId={preCheckoutOrderId}
          onClose={() => setPreCheckoutOrderId(null)}
          onSignIn={() => {}}
          onContinueWithPhone={() => {
            setPendingPhoneOrderId(preCheckoutOrderId);
            setPreCheckoutOrderId(null);
          }}
        />
      )}

      {fulfillmentModalData && (
        <BundleFulfillmentModal
          optionLabel={fulfillmentModalData.option_label}
          onClose={() => setFulfillmentModalData(null)}
          onSubmit={handleFulfillmentSubmit}
          requiredFields={fulfillmentModalData.required_fields}
          initialValues={fulfillmentModalData.initial_values}
        />
      )}

      {pendingPhoneOrderId && (
        <PhoneModal
          orderId={pendingPhoneOrderId}
          onClose={() => setPendingPhoneOrderId(null)}
          onComplete={(orderId) => {
            setPendingPhoneOrderId(null);
            if (STRIPE_CONFIGURED) {
              setPaymentOrderId(orderId);
            } else {
              setLoading(true);
              fetch("/api/payment/confirm", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ order_id: orderId }),
              })
                .then((r) => r.json())
                .then((json) => {
                  if (!json.error) {
                    const addMsg = { role: "assistant" as const, content: json.message || "Payment confirmed! Thank you for your order." };
                    addMessage(addMsg);
                    persistMessage(addMsg);
                    setShowPostCheckoutSignInBanner(true);
                  } else {
                    addMessage({ role: "assistant", content: json.error || "Payment failed." });
                  }
                })
                .catch(() => addMessage({ role: "assistant", content: "Payment failed." }))
                .finally(() => setLoading(false));
            }
          }}
        />
      )}

      {paymentOrderId && (
        <PaymentModal
          orderId={paymentOrderId}
          threadId={threadId}
          onClose={() => setPaymentOrderId(null)}
          onSuccess={() => {
            const confirmMsg = { role: "assistant" as const, content: "Payment confirmed! Thank you for your order." };
            addMessage(confirmMsg);
            persistMessage(confirmMsg);
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
            className="flex-shrink-0 border-t border-[var(--border)] bg-[var(--background)] px-4 py-4"
          >
          {e2eEnabled && bundleId && (
            <div className="mx-auto max-w-3xl flex items-center gap-2 mb-3">
              <button
                type="button"
                onClick={() => handleAction({ action: "view_bundle", bundle_id: bundleId })}
                className="flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm text-[var(--card-foreground)] hover:border-[var(--primary-color)]/50 hover:bg-[var(--primary-color)]/10"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
                View bundle
              </button>
              <button
                type="button"
                onClick={() => handleAction({ action: "checkout", bundle_id: bundleId })}
                className="flex items-center gap-2 rounded-lg border border-[var(--primary-color)] bg-[var(--primary-color)]/20 px-3 py-2 text-sm text-[var(--primary-color)] hover:bg-[var(--primary-color)]/30"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Checkout
              </button>
            </div>
          )}
          <form onSubmit={handleSubmit} className="mx-auto max-w-3xl">
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

      {showPostCheckoutSignInBanner && !isSignedIn && hasClerk && (
        <div className="fixed bottom-20 left-4 right-4 z-50 mx-auto max-w-2xl md:left-1/2 md:right-auto md:-translate-x-1/2">
          <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 p-4 flex items-center justify-between gap-4 shadow-lg">
            <p className="text-sm text-[var(--foreground)]">
              Sign in to save your order, favorites, and conversation history — access them from any device.
            </p>
            <div className="flex items-center gap-2 shrink-0">
              <SignInButton mode="modal">
                <button className="px-4 py-2 rounded-lg bg-[var(--primary-color)] text-[var(--primary-foreground)] text-sm font-medium hover:opacity-90">
                  Sign in
                </button>
              </SignInButton>
              <button
                type="button"
                onClick={() => setShowPostCheckoutSignInBanner(false)}
                className="p-2 rounded-lg text-[var(--muted)] hover:bg-[var(--border)] hover:text-[var(--foreground)]"
                aria-label="Dismiss"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  if (showSideNav) {
    return (
      <div className="flex h-[100dvh] sm:h-screen bg-[var(--background)]">
        <SideNav
          threadId={threadId}
          threads={threads}
          onNewChat={() => handleSelectThread(null)}
          onSelectThread={handleSelectThread}
          onDeleteThread={handleDeleteThread}
          hasUserOrAnonymous={!!(userId || anonymousId)}
          anonymousId={anonymousId ?? undefined}
          collapsed={sideNavCollapsed}
          onToggle={toggleSideNav}
        />
        <div
          className={`flex min-w-0 flex-1 flex-col min-h-0 overflow-hidden transition-[margin] duration-200 ${
            !sideNavCollapsed ? "md:ml-64" : ""
          }`}
        >
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            {chatContent}
          </div>
        </div>
      </div>
    );
  }

  return chatContent;
}
