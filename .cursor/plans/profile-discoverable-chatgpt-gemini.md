# Comprehensive profile discoverable across ChatGPT and Gemini

## Overview

Make the platform's commerce profile discoverable on both ChatGPT (ACP) and Gemini (UCP) with a shared data foundation, **user-controlled push** (single item or all; target ChatGPT and/or Gemini), **ChatGPT 15-minute rate-limit handling**, and **partner portal UI** for ACP/UCP field validation and editing.

---

## 1. Unified data foundation (schema)

- **Partners**: Add/expose seller fields: `seller_name`, `seller_url`, `return_policy_url`, `privacy_policy_url`, `terms_url`, `store_country`, optional `target_countries` (migration in [supabase/migrations/](supabase/migrations/)).
- **Products**: Add or map ACP fields (`url`, `brand`, `is_eligible_search`, `is_eligible_checkout`, availability enum, etc.); UCP uses existing id/name/price/image_url + cents conversion. Use [services/discovery-service/protocols/acp_compliance.py](services/discovery-service/protocols/acp_compliance.py) and [ucp_compliance.py](services/discovery-service/protocols/ucp_compliance.py).

---

## 2. Push controls: single item vs all; target choice (ChatGPT / Gemini / both)

### 2.1 User choices

- **Scope**: User can choose **push single item** (one product) or **push all** (full catalog for the selected target(s)).
- **Target**: User can choose **ChatGPT only**, **Gemini only**, or **both**.
  - **ChatGPT**: Triggers ACP feed generation and delivery (or marks feed as updated for next pull); subject to 15-minute rate limit (see § 3).
  - **Gemini**: UCP catalog is always “live” (API); “push” here means either (a) invalidating/caching if we add a catalog cache, or (b) a **confirmation/validation** action that runs UCP compliance and shows the user what would be served. Option (b) is sufficient for “push to Gemini” in the UI without a separate catalog push.

### 2.2 Backend

- **API**: e.g. `POST /api/v1/feeds/push` (or partner-scoped `POST /api/partners/me/feeds/push`) with body:
  - `scope`: `"single"` | `"all"`
  - `product_id`: required if `scope === "single"`
  - `targets`: `["chatgpt"]` | `["gemini"]` | `["chatgpt", "gemini"]`
- **ChatGPT path**: For `chatgpt` target, generate ACP feed (single product or full catalog), then submit or mark for delivery — **respect 15-minute throttle** (see § 3).
- **Gemini path**: For `gemini` target, either trigger a catalog refresh (if we cache) or run validation and return a summary; no rate limit on our side for UCP (Google calls us).

### 2.3 Where this lives

- **Partner portal**: “Commerce / AI catalog” or “Discovery” section with:
  - Buttons: “Push to ChatGPT”, “Push to Gemini”, “Push to both”
  - Scope: “This product only” (when viewing a product) or “Entire catalog” (e.g. from a catalog/settings page)
- **Platform admin** (optional): Same push controls for platform-wide or per-partner feed.

---

## 3. ChatGPT 15-minute catalog update rate limit

### 3.1 Constraint

- ChatGPT has a **15-minute minimum interval** between catalog updates. We must not attempt to push more often than that (per feed / per partner, depending on how OpenAI counts it).

### 3.2 Handling

- **Store last push time**: Persist `last_acp_push_at` (and optionally `last_acp_push_scope`) per partner (or per platform if single feed). Store in DB (e.g. `partners` or a small `feed_push_state` table) or in platform config.
- **Before pushing to ChatGPT**:
  - If `last_acp_push_at` is within the last 15 minutes, **reject** the push with a clear message: “Catalog can be updated again at {time}” (next allowed time).
  - Optionally show a **countdown** in the UI.
- **After a successful push**: Update `last_acp_push_at` to now.
- **UI**: When user selects “Push to ChatGPT” (or “Push to both”):
  - If within 15-minute window: disable button or show “Next update available in X minutes” and next-allowed timestamp.
  - If outside window: allow push; after success, show “Next update available after {time}”.

### 3.3 Optional: queue

- For “push all” or high volume, optionally **queue** the push and process at the next allowed slot instead of rejecting. Simpler MVP: reject and show next-allowed time; queue can be a later enhancement.

---

## 4. Partner portal UI: ACP / UCP fields for validation and update

### 4.1 Goal

- Partners see the **ACP and UCP fields** that affect discovery and can **validate** (see compliance status) and **update** them.

### 4.2 Partner-level (seller) fields

- **Location**: Partner **Settings** or a dedicated “Commerce profile” / “AI catalog profile” section in the partner portal.
- **Fields** (from [COMMERCE_FEED_SCHEMA_REQUIREMENTS.md](docs/COMMERCE_FEED_SCHEMA_REQUIREMENTS.md) and ACP/UCP docs):
  - `seller_name` (e.g. business name)
  - `seller_url`
  - `return_policy_url`
  - `privacy_policy_url`
  - `terms_url`
  - `store_country`
  - `target_countries` (optional)
- **UI**: Form with these fields; save to `partners` (or partner profile API). Show **validation** (e.g. “Used for ChatGPT and Gemini discovery”) and optional **preview** of how the partner will appear as seller on a product row.

### 4.3 Product-level (ACP/UCP) fields

- **Location**: **Product edit** flow (e.g. [apps/portal/app/(partner)/products/[id]/product-edit-form.tsx](apps/portal/app/(partner)/products/[id]/product-edit-form.tsx)) or a “Discovery” tab per product.
- **Fields** (product-level ACP/UCP):
  - `url` (product page)
  - `brand`
  - `image_url` (if not already in main form)
  - `is_eligible_search` / `is_eligible_checkout` (booleans)
  - `availability` (or map from `is_available`)
  - `target_countries` / `store_country` if not only at partner level
- **Validation**: Before push (or on blur), call an API that runs ACP/UCP validation (e.g. `validate_product_acp`, `validate_product_ucp`) and show **warnings/errors** (missing required, prohibited content). Allow user to fix and re-validate.

### 4.4 Validation API

- **Endpoint**: e.g. `GET /api/products/{id}/validate-discovery` or `POST /api/partners/me/validate-discovery` with product payload.
- **Response**: `{ acp: { valid, errors, warnings }, ucp: { valid, errors } }` so the UI can show “Ready for ChatGPT” / “Ready for Gemini” and list issues.

### 4.5 Summary

- **Partner settings**: Form for seller (ACP/UCP) fields; save and optional preview.
- **Product edit**: ACP/UCP product fields + validation; show compliance status and block or warn on push if invalid (optional).

---

## 5. UCP (Gemini) – discoverable profile and catalog

- **`/.well-known/ucp`**: Implement on discovery service; return UCP Business Profile (version, services, capabilities, rest.endpoint). See [AI_PLATFORM_PRODUCT_DISCOVERY.md](docs/AI_PLATFORM_PRODUCT_DISCOVERY.md) § 3.1.
- **UCP catalog API**: `GET /api/v1/ucp/items` (or `/catalog`) with `q`, `limit`; wrap discovery and map to UCP Item shape (id, title, price cents, image_url); use [ucp_compliance.py](services/discovery-service/protocols/ucp_compliance.py).

---

## 6. ACP (ChatGPT) – feed export and delivery

- **Feed export**: Products JOIN partners → ACP-shaped rows; ACP validation; output jsonl.gz/csv.gz. Support **single product** or **full catalog** for push.
- **Public feed URL**: e.g. `GET /api/v1/feeds/acp` (and optional `?partner_id=`) or static artifact; document for OpenAI.
- **Registration**: OpenAI merchant/feed onboarding; point to feed URL. **Rate limit**: enforce 15-minute minimum between updates (see § 3).

---

## 7. Implementation order (with new items)

| Step | Deliverable |
|------|-------------|
| 1 | Schema: partners seller fields; products ACP fields (or metadata). |
| 2 | **Partner portal**: Partner settings form for ACP/UCP seller fields; product edit (or Discovery tab) for ACP/UCP product fields. |
| 3 | **Validation API**: Product/partner discovery validation (ACP + UCP) for UI. |
| 4 | **Push API**: `POST .../feeds/push` with scope (single/all), targets (chatgpt/gemini/both); store `last_acp_push_at`; enforce 15-minute throttle for ChatGPT. |
| 5 | **Partner portal**: Push controls (single vs all, ChatGPT / Gemini / both); show 15-min countdown and next-allowed time for ChatGPT. |
| 6 | UCP: `/.well-known/ucp` + UCP catalog endpoint. |
| 7 | ACP: Feed export (single + full), public feed URL, OpenAI registration. |
| 8 | Docs: Update [AI_PLATFORM_PRODUCT_DISCOVERY.md](docs/AI_PLATFORM_PRODUCT_DISCOVERY.md) with push behavior and rate limit. |

---

## Key files

- [docs/AI_PLATFORM_PRODUCT_DISCOVERY.md](docs/AI_PLATFORM_PRODUCT_DISCOVERY.md)
- [docs/COMMERCE_FEED_SCHEMA_REQUIREMENTS.md](docs/COMMERCE_FEED_SCHEMA_REQUIREMENTS.md)
- [services/discovery-service/protocols/ucp_compliance.py](services/discovery-service/protocols/ucp_compliance.py)
- [services/discovery-service/protocols/acp_compliance.py](services/discovery-service/protocols/acp_compliance.py)
- [apps/portal/app/(partner)/settings/page.tsx](apps/portal/app/(partner)/settings/page.tsx) – add Commerce/ACP-UCP section
- [apps/portal/app/(partner)/products/[id]/product-edit-form.tsx](apps/portal/app/(partner)/products/[id]/product-edit-form.tsx) – add ACP/UCP fields and validation
