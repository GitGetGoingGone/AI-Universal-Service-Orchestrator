/** HTTP client for Orchestrator and Discovery APIs. */

const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || "http://localhost:8002";
const DISCOVERY_URL = process.env.DISCOVERY_URL || "http://localhost:8000";
const TIMEOUT = 30000;

async function fetchJson(
  url: string,
  options: RequestInit = {}
): Promise<unknown> {
  const res = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
    signal: AbortSignal.timeout(TIMEOUT),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

export async function discoverProducts(
  query: string,
  limit = 20,
  partnerId?: string
): Promise<unknown> {
  const params = new URLSearchParams({ intent: query, limit: String(limit) });
  if (partnerId) params.set("partner_id", partnerId);
  return fetchJson(`${DISCOVERY_URL}/api/v1/discover?${params}`);
}

export async function getProductDetails(productId: string): Promise<unknown> {
  return fetchJson(`${ORCHESTRATOR_URL}/api/v1/products/${productId}`);
}

export async function getBundleDetails(bundleId: string): Promise<unknown> {
  return fetchJson(`${ORCHESTRATOR_URL}/api/v1/bundles/${bundleId}`);
}

export async function addToBundle(
  productId: string,
  userId?: string,
  bundleId?: string
): Promise<unknown> {
  return fetchJson(`${ORCHESTRATOR_URL}/api/v1/bundle/add`, {
    method: "POST",
    body: JSON.stringify({ product_id: productId, user_id: userId, bundle_id: bundleId }),
  });
}

export async function removeFromBundle(itemId: string): Promise<unknown> {
  return fetchJson(`${ORCHESTRATOR_URL}/api/v1/bundle/remove`, {
    method: "POST",
    body: JSON.stringify({ item_id: itemId }),
  });
}

export async function proceedToCheckout(bundleId: string): Promise<unknown> {
  return fetchJson(`${ORCHESTRATOR_URL}/api/v1/checkout`, {
    method: "POST",
    body: JSON.stringify({ bundle_id: bundleId }),
  });
}

export async function createPaymentIntent(orderId: string): Promise<unknown> {
  return fetchJson(`${ORCHESTRATOR_URL}/api/v1/payment/create`, {
    method: "POST",
    body: JSON.stringify({ order_id: orderId }),
  });
}

export async function requestChange(
  orderId: string,
  orderLegId: string,
  partnerId: string,
  originalItem: Record<string, unknown>,
  requestedChange: Record<string, unknown>,
  respondBy?: string
): Promise<unknown> {
  return fetchJson(`${ORCHESTRATOR_URL}/api/v1/change-request`, {
    method: "POST",
    body: JSON.stringify({
      order_id: orderId,
      order_leg_id: orderLegId,
      partner_id: partnerId,
      original_item: originalItem,
      requested_change: requestedChange,
      respond_by: respondBy,
    }),
  });
}

export async function getManifest(): Promise<unknown> {
  return fetchJson(`${ORCHESTRATOR_URL}/api/v1/manifest`);
}

export async function trackOrder(orderId: string): Promise<unknown> {
  return fetchJson(`${ORCHESTRATOR_URL}/api/v1/orders/${orderId}/status`);
}

export async function classifySupport(
  conversationRef: string,
  messageContent: string
): Promise<unknown> {
  return fetchJson(`${ORCHESTRATOR_URL}/api/v1/classify-support`, {
    method: "POST",
    body: JSON.stringify({
      conversation_ref: conversationRef,
      message_content: messageContent,
    }),
  });
}

export async function createReturn(
  orderId: string,
  partnerId: string,
  params?: {
    reason?: string;
    reason_detail?: string;
    order_leg_id?: string;
    requester_id?: string;
    items?: unknown[];
    refund_amount_cents?: number;
  }
): Promise<unknown> {
  return fetchJson(`${ORCHESTRATOR_URL}/api/v1/returns`, {
    method: "POST",
    body: JSON.stringify({
      order_id: orderId,
      partner_id: partnerId,
      ...params,
    }),
  });
}
