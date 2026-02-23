# Current orchestrator shapes vs UCP-compliant target

Since we're not in production yet, we can change formats. **Target: UCP only — no legacy or non-UCP flows.** This doc describes how the orchestrator currently structures product list, checkout, and payment and how to replace that with UCP parts and standard ProductCard, Checkout, and Payment components.

---

## 1. Product list (discovery results)

### Current (orchestrator → client)

- **Source:** `agentic/loop.py` → `_discover_composite()` builds:
  - `data.categories`: list of `{ "query": "<category>", "products": [ ... ] }`
  - `data.products`: flat list of all products
  - `data.suggested_bundle_options`: optional list of `{ label, description, product_ids, product_names, total_price, currency, categories }`
- **Card:** `packages/shared/adaptive_cards/experience_card.py` → `generate_experience_card()` builds a single **Adaptive Card** JSON:
  - Sections per category; per product: name, price, description, image_url, and actions `Add to Bundle`, `Favorite`, `Details` with `data: { action, product_id }`
  - Or suggested bundle options with "Add &lt;label&gt;" and `data: { action: "add_bundle_bulk", product_ids, option_label, fulfillment_fields }`
- **Wire:** Chat API returns (stream `done` or non-stream):
  - `summary` (text)
  - `adaptive_card` (one big Adaptive Card JSON)
  - `data`: `{ intent, products, categories, suggested_bundle_options, engagement, ... }`
  - `suggested_ctas` when adaptive cards are off: e.g. `[{ label: "Add to bundle", action: "add_to_bundle" }, ...]`

**Product shape (from discovery DB / loop):**  
`id`, `name`, `description`, `price`, `currency`, `image_url`, `capabilities`, `partner_id`, `url`, `brand`, `experience_tags`, etc.

### UCP target (for ProductCard)

- **Message part:** Use a **part** in the response (not only inside an adaptive card) with type like `a2a.product_results` (or the current UCP name for product listing).
- **Payload:** Array of products in UCP product shape, e.g.:
  - `productID`, `name`, `image` (array), `brand: { name }`, `offers: { price, priceCurrency, availability }`, `url`, `description`, etc. (see [UCP samples chat-client types](https://github.com/Universal-Commerce-Protocol/samples/blob/main/a2a/chat-client/types.ts)).
- **Action:** "Add to cart/checkout" sends a standard part, e.g. `{ action: "add_to_checkout", product_id, quantity }` (or UCP-equivalent).

**Concrete change:**  
- In the **orchestrator** (or in the Next.js adapter that translates to AI SDK stream): when returning discovery results, **also** (or instead of) building one adaptive card, emit a **structured part** with UCP product shape (map `id`→`productID`, `price`→`offers.price`, `image_url`→`image[]`, etc.).  
- **Client:** Render that part with a **ProductCard** component that only knows UCP product shape and sends the standard add-to-checkout action.

---

## 2. Checkout (order summary, proceed to payment)

### Current (orchestrator + discovery + client)

- **Trigger:** User taps "Proceed to Checkout" on the **bundle card** (from `packages/shared/adaptive_cards/bundle_card.py`: action `checkout`, `bundle_id`).
- **Flow:**
  1. **Client** → `POST /api/checkout` with `{ bundle_id }` (uso-unified-chat calls Next.js route → orchestrator `POST /api/v1/checkout` → discovery `POST /api/v1/checkout`).
  2. **Discovery** `api/products.py` (or similar): `create_order_from_bundle(bundle_id)` → inserts `orders` + `order_items` + `order_legs`; returns order object with `id`, `total`, `currency`, `line_items`-like data.
  3. **Orchestrator** returns that order to the client; client stores `latestOrder` and can show **checkout card** (from `packages/shared/adaptive_cards/checkout_card.py`): line items, totals, actions "Complete Checkout" (`complete_checkout`, `order_id`) and "Edit Order".
- **Checkout card input:** `generate_checkout_card(order, line_items)` expects `order` with `id`, `bundle_id`, `subtotal`, `total`, `currency`, `line_items` (each: `name`, `quantity`, `price`, `currency`).

**Wire (today):**  
- No dedicated “checkout” part in the chat response. Checkout appears when the user clicks “Proceed to Checkout” and the client gets the order from `POST /api/checkout`; then the client adds a message with `adaptiveCard: json.adaptive_card` (checkout card) and/or stores `latestOrder` for “Proceed to payment” CTA.

### UCP target (for Checkout component)

- **Message part:** `a2a.ucp.checkout` (or equivalent) with UCP checkout schema:
  - `id`, `line_items[]` (each: `id`, `item: { id, title, price, image_url }`, `quantity`, `totals[]`), `currency`, `totals[]`, `status`, `payment: { handlers[], instruments[] }`, `continue_url`, etc. (see [UCP samples](https://github.com/Universal-Commerce-Protocol/samples/blob/main/a2a/chat-client/types.ts) and discovery `ucp_checkout.py`).
- **Discovery** already has `_order_to_ucp_checkout()` in `services/discovery-service/api/ucp_checkout.py`: converts order to UCP checkout shape (`line_items`, `totals`, `payment.handlers`, `continue_url`, etc.).

**Concrete change:**  
- When the client receives an order (after checkout or when showing “order summary” in chat), the backend should return a **part** with type `a2a.ucp.checkout` and payload from `_order_to_ucp_checkout(order)` (or equivalent).  
- **Client:** Render that part with a **Checkout** component that only knows UCP checkout shape; “Start payment” triggers the standard flow (e.g. open `continue_url` or payment handler).

---

## 3. Payment (create intent, confirm, return URL)

### Current (orchestrator + payment service + client)

- **Trigger:** User taps "Complete Checkout" or "Proceed to payment"; client has `order_id` (from `latestOrder` or checkout response).
- **Flow:**
  1. **Client** opens **PaymentModal** (uso-unified-chat `PaymentModal.tsx`); calls `POST /api/payment/create` with `{ order_id }` (and optionally `thread_id`).  
  2. **Next.js** → orchestrator or payment service: `orchestrator-service/clients.py` → `create_payment_intent(order_id)` → **Payment service** `POST /api/v1/payment/create` → returns Stripe client secret etc.  
  3. Client uses Stripe.js to confirm payment; on success, redirect to `...?payment_success=1&order_id=...&thread_id=...`.  
  4. **Confirm (demo):** `POST /api/payment/confirm` with `{ order_id }` → payment service marks order paid.
- **No UCP payment parts in chat today:** Payment is out-of-band (modal + redirect). The chat only gets `order_id` and shows “Proceed to payment” CTA; no payment method selector or payment instrument in the message stream.

### UCP target (for Payment components)

- **Message parts:**  
  - Checkout part includes `payment: { handlers[], instruments[] }` (already in discovery `_order_to_ucp_checkout`).  
  - When the client needs to collect payment method: show **PaymentMethodSelector** (from credential provider / payment handler).  
  - When user selects method and authorizes: send part with payment instrument (e.g. `a2a.ucp.checkout.payment_data`).  
  - Backend completes checkout with that instrument (or redirects to `continue_url` for Stripe).
- **UCP samples** (a2a chat-client): `handlePaymentMethodSelection(checkout)` → get payment methods from credential provider → add message with `paymentMethods`; `handlePaymentMethodSelected` → get token → add message with `paymentInstrument`; `handleConfirmPayment` → send `complete_checkout` + payment data.

**Concrete change:**  
- **Backend:** When returning checkout, use UCP checkout shape including `payment.handlers` (and optionally `instruments`). Support a “complete checkout” action that accepts UCP payment data.  
- **Client:** Use **PaymentMethodSelector** and **PaymentConfirmation** components when the checkout part has `payment.handlers`; on confirm, send the standard complete_checkout + payment_data part. No legacy PaymentModal or non-UCP redirect flows.

**Stripe via UCP payment.handlers (yes):** Use UCP `payment.handlers` to show Stripe as the payment option. Discovery already returns `payment.handlers: [{"type": "stripe", "provider": "stripe"}]` in `_order_to_ucp_checkout()` (`services/discovery-service/api/ucp_checkout.py`). The client **PaymentMethodSelector** should render one option per handler — e.g. "Pay with Stripe" when a handler has `type` or `id` `"stripe"`. For Stripe, the client can then (1) **redirect** to `continue_url` (e.g. `/pay?order_id=...`) for the existing Stripe page, or (2) **inline** use Stripe.js and send the payment method token as `a2a.ucp.checkout.payment_data` in the complete_checkout action. Optionally add per-handler `id`, `name`, and `config` (e.g. `continue_url` or Stripe publishable key) so the client knows how to invoke Stripe. Stripe remains the payment option, exposed in a UCP-compliant way.

---

## 4. Where each piece lives (codebase)

| Concern              | Current location                                                                 | UCP-aligned change |
|----------------------|-----------------------------------------------------------------------------------|--------------------|
| **Product list**     | `loop.py` → `data.categories` / `data.products`; `experience_card.py` → one card  | Emit UCP product_results part (orchestrator or adapter); client ProductCard |
| **Bundle / add**     | `experience_card.py` actions `add_to_bundle`, `add_bundle_bulk`; client handles   | Map to add_to_checkout (product_id, quantity) or keep bundle semantics with UCP-style part |
| **Checkout**         | Discovery `create_order_from_bundle`; `checkout_card.py`; client POST /api/checkout | Return `a2a.ucp.checkout` part (use `_order_to_ucp_checkout`); client Checkout component |
| **Payment**          | Payment service Stripe; client PaymentModal, /api/payment/create, /api/payment/confirm | UCP only: payment.handlers in checkout part; client PaymentMethodSelector + PaymentConfirmation; complete_checkout with payment_data. No legacy flows. |

---

## 5. Suggested order of changes (no backward compatibility needed)

1. **Define a single “chat response part” format** for the client (e.g. alongside or instead of `adaptive_card`): e.g. `parts: [{ type: "text", text }, { type: "a2a.product_results", results, content }, { type: "a2a.ucp.checkout", ... }]`.  
2. **Orchestrator (or Next.js adapter):** When returning discovery results, add a part with UCP product shape; when returning an order (after checkout), add a part with `_order_to_ucp_checkout(order)`.  
3. **Client:** Add **ProductCard**, **Checkout**, and **Payment** components that only consume these part types; render them when the message contains the corresponding part.  
4. **Remove** the monolithic `adaptive_card` for products/checkout; use only UCP parts. No legacy or non-UCP flows.  
5. **Payment:** Extend checkout part with handlers; add client payment method selection and confirm flow that sends UCP-style payment_data on complete_checkout. UCP-only; no fallback to current PaymentModal or non-UCP payment paths.

Target: UCP only. Orchestrator and client use only UCP part types and standard ProductCard, Checkout, and Payment components.
