"use client";

import React, { useEffect, useMemo } from "react";
import { Loader2 } from "lucide-react";
import { useAuiState } from "@assistant-ui/react";
import { CHAT_STORAGE_MA_IN_FLIGHT } from "@/lib/chat-storage-keys";
import { useGatewayAction } from "@/contexts/GatewayActionContext";
import { PaymentFormInline } from "./PaymentFormInline";
import { AgentHuddle, type AgentRow, type TodoItem, type ThoughtLine } from "./AgentHuddle";

type Product = {
  id?: string;
  name?: string;
  price?: number;
  currency?: string;
  image_url?: string;
};

type BundleOption = {
  option_label?: string;
  product_ids?: string[];
  [k: string]: unknown;
};

function ProductListRenderer({ data }: { data: { products?: Product[] } }) {
  const onAction = useGatewayAction();
  const products = data.products ?? [];
  if (products.length === 0) return null;
  return (
    <div className="my-3 grid gap-2 sm:grid-cols-2">
      {products.slice(0, 6).map((p, i) => (
        <div
          key={p.id ?? i}
          className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm dark:border-gray-700 dark:bg-gray-800"
        >
          {p.image_url && (
            <img
              src={p.image_url}
              alt={p.name ?? "Product"}
              className="mb-2 h-24 w-full rounded object-cover"
            />
          )}
          <div className="font-medium text-gray-900 dark:text-gray-100">
            {p.name ?? "Product"}
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400">
            {p.currency ?? "USD"} {(p.price ?? 0).toFixed(2)}
          </div>
          {onAction && p.id && (
            <div className="mt-2 flex flex-wrap gap-1">
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onAction({ action: "add_to_bundle", product_id: p.id! });
                }}
                className="rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700"
              >
                Add to bundle
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onAction({
                    action: "explore_product",
                    product_id: p.id!,
                    product_name: p.name,
                  });
                }}
                className="rounded border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
              >
                Explore
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ThematicOptionsRenderer({
  data,
}: { data: { options?: BundleOption[] } }) {
  const onAction = useGatewayAction();
  const options = data.options ?? [];
  if (options.length === 0) return null;
  return (
    <div className="my-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {options.map((opt, i) => (
        <div
          key={i}
          className="flex flex-col rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-800"
        >
          <div className="mb-3 flex-1 font-medium text-gray-900 dark:text-gray-100">
            {opt.option_label ?? `Option ${i + 1}`}
          </div>
          {opt.description != null && String(opt.description).trim() !== "" ? (
            <div className="mb-3 text-sm text-gray-600 dark:text-gray-400">
              {String(opt.description)}
            </div>
          ) : null}
          {onAction && (
            <button
              type="button"
              onClick={() =>
                onAction({
                  action: "explore_theme",
                  option_label: opt.option_label ?? `Option ${i + 1}`,
                })
              }
              className="mt-auto rounded border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
            >
              Explore more options
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

function EngagementChoiceRenderer({
  data,
}: {
  data: {
    ctas?: { label?: string; action?: string; order_id?: string; bundle_id?: string }[];
    options?: BundleOption[];
  };
}) {
  const onAction = useGatewayAction();
  const ctas = data.ctas ?? [];
  const options = data.options ?? [];
  if (ctas.length === 0) return null;
  return (
    <div className="my-3 flex flex-wrap gap-2">
      {ctas.map((cta, i) => (
        <button
          key={i}
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            if (!onAction) return;
            if (cta.action === "add_to_bundle") {
              const first = options[0];
              if (first?.product_ids?.length) {
                onAction({
                  action: "add_bundle_bulk",
                  product_ids: first.product_ids,
                  option_label: first.option_label,
                });
              }
            } else if (cta.action === "proceed_to_payment" && cta.order_id) {
              onAction({ action: "proceed_to_payment", order_id: cta.order_id });
            } else if (cta.action === "view_bundle" && cta.bundle_id) {
              onAction({ action: "view_bundle", bundle_id: cta.bundle_id });
            }
          }}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {cta.label ?? cta.action ?? "Action"}
        </button>
      ))}
    </div>
  );
}

type ExperienceLeg = {
  id?: string;
  partner_name?: string | null;
  product_id?: string;
  status?: string;
};
type ExperienceSessionData = {
  id?: string;
  thread_id?: string;
  status?: string;
  legs?: ExperienceLeg[];
};

function ExperienceSessionRenderer({ data }: { data: ExperienceSessionData }) {
  const legs = (data?.legs ?? []) as ExperienceLeg[];
  if (legs.length === 0) {
    return (
      <div className="my-3 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
        <span className="font-medium">Experience Session</span>
        <p className="mt-1">
          Status: <span className="font-mono">{data?.status ?? "active"}</span>
        </p>
        <p className="text-xs mt-2 text-gray-500">No legs yet. Add products to your bundle to see progress.</p>
      </div>
    );
  }
  return (
    <div className="my-3 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
      <span className="font-medium">Experience Session</span>
      <p className="mt-1 text-xs">
        Status: <span className="font-mono">{data?.status ?? "active"}</span>
      </p>
      <ul className="mt-3 space-y-2">
        {legs.map((leg, i) => (
          <li key={leg.id ?? i} className="flex items-center gap-2">
            <span
              className={`inline-flex h-2 w-2 rounded-full ${
                leg.status === "committed"
                  ? "bg-green-500"
                  : leg.status === "in_customization"
                    ? "bg-amber-500 animate-pulse"
                    : leg.status === "ready"
                      ? "bg-blue-500"
                      : "bg-gray-400"
              }`}
              aria-hidden
            />
            <span className="font-medium text-gray-800 dark:text-gray-200">
              {leg.partner_name ?? "Partner"}
            </span>
            <span className="text-xs text-gray-500">— {leg.status ?? "pending"}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ThinkingRenderer({ data, isLive }: { data: { text?: string }; isLive?: boolean }) {
  return (
    <div
      className={
        isLive
          ? "my-2 flex items-center gap-2 rounded-lg bg-[var(--muted)]/30 px-3 py-2 text-sm text-[var(--foreground)]"
          : "my-2 text-sm italic text-gray-500 dark:text-gray-400"
      }
    >
      {isLive && (
        <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--primary)]" aria-hidden />
      )}
      {data.text ?? "Thinking..."}
    </div>
  );
}

function PaymentFormRenderer({
  data,
}: {
  data: { order_id?: string };
}) {
  const orderId = data?.order_id;
  if (!orderId || typeof orderId !== "string") return null;
  return <PaymentFormInline orderId={orderId} />;
}

type DataPartProps = { name?: string; data?: unknown; isLive?: boolean };

/** AI SDK stream chunks use `type: "data-<name>"`; legacy parts may use `type: "data"` + `name`. */
function getDataStreamPartName(part: { type?: string; name?: string }): string | null {
  if (part.type === "data" && typeof part.name === "string" && part.name.length > 0) {
    return part.name;
  }
  if (typeof part.type === "string" && part.type.startsWith("data-")) {
    return part.type.slice("data-".length);
  }
  return null;
}

function contentHasAgentHuddle(content: unknown[] | undefined): boolean {
  if (!Array.isArray(content)) return false;
  return content.some((part) => {
    if (!part || typeof part !== "object") return false;
    return getDataStreamPartName(part as { type?: string; name?: string }) === "agent_huddle";
  });
}

function readMultiAgentInFlight(): boolean {
  if (typeof window === "undefined") return false;
  return sessionStorage.getItem(CHAT_STORAGE_MA_IN_FLIGHT) === "1";
}

/** Shown while the assistant message streams and multi-agent mode was requested, before the final huddle part arrives. */
function MultiAgentFlightPlaceholder() {
  return (
    <section
      className="agent-huddle-root my-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 text-[var(--card-foreground)] shadow-sm"
      aria-live="polite"
      aria-label="Concierge scouts in progress"
    >
      <div className="mb-2 flex flex-wrap items-center gap-2 border-b border-[var(--border)] pb-2 text-sm font-medium text-[var(--foreground)]">
        <Loader2 className="h-4 w-4 shrink-0 animate-spin text-[var(--primary,#2563eb)]" aria-hidden />
        <span>Working with your concierge team</span>
      </div>
      <p className="text-sm leading-relaxed text-[var(--foreground)]/90">
        Scouts are checking inventory, partner catalogs, and context. Full status, memory, and reasoning traces
        will appear here as each step completes.
      </p>
    </section>
  );
}

const DATA_RENDERERS_BY_NAME: Record<string, React.ComponentType<DataPartProps>> = {
  product_list: ProductListRenderer as React.ComponentType<DataPartProps>,
  thematic_options: ThematicOptionsRenderer as React.ComponentType<DataPartProps>,
  engagement_choice: EngagementChoiceRenderer as React.ComponentType<DataPartProps>,
  experience_session: ExperienceSessionRenderer as React.ComponentType<DataPartProps>,
  thinking: ThinkingRenderer as React.ComponentType<DataPartProps>,
  payment_form: PaymentFormRenderer as React.ComponentType<DataPartProps>,
  thread_metadata: ThreadMetadataRenderer as React.ComponentType<DataPartProps>,
  agent_huddle: AgentHuddleRenderer as React.ComponentType<DataPartProps>,
};

function ThreadMetadataRenderer() {
  return null;
}

function AgentHuddleRenderer({
  data,
}: {
  data: {
    multi_agent_status?: { agents?: unknown[] };
    todos?: { label?: string; status?: string }[];
    thought_timelines?: { label?: string; duration_ms?: number; detail?: string }[];
    memory_health?: { label?: string; status?: string; detail?: string };
    credit_usage?: { estimated_total_tokens?: number; note?: string };
  };
}) {
  const agents = data.multi_agent_status?.agents;
  const status =
    agents && Array.isArray(agents)
      ? { agents: agents as AgentRow[] }
      : undefined;
  return (
    <AgentHuddle
      multi_agent_status={status}
      todos={data.todos as TodoItem[] | undefined}
      thought_timelines={data.thought_timelines as ThoughtLine[] | undefined}
      memory_health={data.memory_health}
      credit_usage={data.credit_usage}
    />
  );
}

function DataPartFallback({ name, data }: { name: string; data: unknown }) {
  return (
    <div className="my-2 text-xs text-gray-500">
      [{name}] <pre className="inline">{JSON.stringify(data)}</pre>
    </div>
  );
}

/** Render assistant message parts manually to avoid scope.dataRenderers (not set by AI SDK runtime).
 * Thinking parts are shown only while this message is streaming (progress visible); hidden when complete.
 */
export function GatewayMessageParts() {
  const content = useAuiState((s) => s.message.content);
  const isRunning = useAuiState((s) => s.thread.isRunning);
  const isLastMessage = useAuiState((s) => s.message.isLast ?? true);
  const showThinking = Boolean(isRunning && isLastMessage);

  useEffect(() => {
    if (!isRunning && typeof window !== "undefined") {
      sessionStorage.removeItem(CHAT_STORAGE_MA_IN_FLIGHT);
    }
  }, [isRunning]);

  if (!Array.isArray(content)) {
    if (showThinking) {
      return (
        <div className="space-y-2">
          <div className="flex items-center gap-2 rounded-lg bg-[var(--muted)]/30 px-3 py-2 text-sm text-[var(--foreground)]">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--primary)]" aria-hidden />
            Thinking...
          </div>
          {readMultiAgentInFlight() ? <MultiAgentFlightPlaceholder /> : null}
        </div>
      );
    }
    return null;
  }

  const lastAgentHuddleIndex = useMemo(() => {
    let last = -1;
    content.forEach((part, i) => {
      if (!part || typeof part !== "object") return;
      if (getDataStreamPartName(part as { type?: string; name?: string }) === "agent_huddle") last = i;
    });
    return last;
  }, [content]);

  const hasThinkingParts = content.some((part) => {
    if (typeof part !== "object" || part === null) return false;
    return getDataStreamPartName(part as { type?: string; name?: string }) === "thinking";
  });

  // Only show the latest thinking part so status messages don't stack
  const lastThinkingIndex = content.reduce<number>((last, part, i) => {
    if (typeof part !== "object" || part === null) return last;
    return getDataStreamPartName(part as { type?: string; name?: string }) === "thinking" ? i : last;
  }, -1);

  return (
    <div className="space-y-1">
      {showThinking && !hasThinkingParts && (
        <div className="flex items-center gap-2 rounded-lg bg-[var(--muted)]/30 px-3 py-2 text-sm text-[var(--foreground)]">
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--primary)]" aria-hidden />
          Understanding what you&apos;re looking for...
        </div>
      )}
      {showThinking && readMultiAgentInFlight() && !contentHasAgentHuddle(content) ? (
        <MultiAgentFlightPlaceholder />
      ) : null}
      {content.map((part, index) => {
        if (!part || typeof part !== "object") return null;
        const p = part as { type?: string; text?: string; name?: string; data?: unknown };
        if (p.type === "text" && typeof p.text === "string") {
          return (
            <div key={index} className="whitespace-pre-wrap text-[var(--foreground)]">
              {p.text}
            </div>
          );
        }
        const dataName = getDataStreamPartName(p);
        if (dataName) {
          if (dataName === "agent_huddle" && index !== lastAgentHuddleIndex) {
            return null;
          }
          if (dataName === "thinking") {
            if (!showThinking) return null;
            // Only render the latest thinking part so status messages don't stack
            if (index !== lastThinkingIndex) return null;
            const Renderer = DATA_RENDERERS_BY_NAME.thinking;
            return <Renderer key={index} name={dataName} data={p.data ?? {}} isLive />;
          }
          const Renderer = DATA_RENDERERS_BY_NAME[dataName] ?? DataPartFallback;
          return <Renderer key={index} name={dataName} data={p.data ?? {}} />;
        }
        return null;
      })}
    </div>
  );
}
