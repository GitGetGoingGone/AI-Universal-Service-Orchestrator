"use client";

import { MessagePrimitive } from "@assistant-ui/react";
import { useGatewayAction } from "@/contexts/GatewayActionContext";

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
            <div className="mt-2">
              <button
                type="button"
                onClick={() =>
                  onAction({ action: "add_to_bundle", product_id: p.id! })
                }
                className="rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700"
              >
                Add to bundle
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
    <div className="my-3 flex flex-wrap gap-2">
      {options.map((opt, i) => (
        <button
          key={i}
          type="button"
          onClick={() => {
            if (
              onAction &&
              Array.isArray(opt.product_ids) &&
              opt.product_ids.length > 0
            ) {
              onAction({
                action: "add_bundle_bulk",
                product_ids: opt.product_ids,
                option_label: opt.option_label,
              });
            }
          }}
          className="rounded-full border border-gray-300 bg-gray-50 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
        >
          {opt.option_label ?? `Option ${i + 1}`}
        </button>
      ))}
    </div>
  );
}

function EngagementChoiceRenderer({
  data,
}: {
  data: {
    ctas?: { label?: string; action?: string; order_id?: string }[];
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
          onClick={() => {
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

function ExperienceSessionRenderer({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="my-3 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
      <pre className="whitespace-pre-wrap">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

function ThinkingRenderer({ data }: { data: { text?: string } }) {
  return (
    <div className="my-2 text-sm italic text-gray-500 dark:text-gray-400">
      {data.text ?? "Thinking..."}
    </div>
  );
}

export const gatewayDataComponents = {
  by_name: {
    product_list: ProductListRenderer,
    thematic_options: ThematicOptionsRenderer,
    engagement_choice: EngagementChoiceRenderer,
    experience_session: ExperienceSessionRenderer,
    thinking: ThinkingRenderer,
  },
  Fallback: ({ name, data }: { name: string; data: unknown }) => (
    <div className="my-2 text-xs text-gray-500">
      [{name}] <pre className="inline">{JSON.stringify(data)}</pre>
    </div>
  ),
};

/** Single Parts component: Text + Gateway data parts for MessagePrimitive.Parts */
export function GatewayMessageParts() {
  return (
    <MessagePrimitive.Parts
      components={{
        Text: () => (
          <MessagePrimitive.Text className="whitespace-pre-wrap text-gray-800 dark:text-gray-200" />
        ),
        data: gatewayDataComponents,
      }}
    />
  );
}
