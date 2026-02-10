# Commerce Feed Schema Requirements (ACP + UCP)

This document defines **schema requirements** for product data used in AI commerce flows: **OpenAI ACP** (ChatGPT) and **Google UCP** (AI Mode, Gemini). It also maps these to our **platform schema** and a **unified canonical** shape.

---

## 1. Overview

| Protocol | Purpose | Product/catalog role |
|----------|---------|----------------------|
| **ACP** (OpenAI) | [Product Feed Spec](https://developers.openai.com/commerce/specs/feed) – merchants share a **product feed** (jsonl.gz/csv.gz) for discovery and checkout in ChatGPT. | Full product feed with many required/optional fields. |
| **UCP** (Google) | [UCP Specification](https://ucp.dev/specification/overview/) – businesses expose `/.well-known/ucp` and **checkout/order** APIs. Product appears as **Item** in line items. | Item in checkout: `id`, `title`, `price` (required), `image_url` (optional). No separate “feed spec”; catalog is whatever the business exposes. |

So: **ACP** has a detailed **product feed schema**; **UCP** has a minimal **item schema** for the checkout flow. Both can share the same **prohibited content** policy for consistency.

---

## 2. ACP (OpenAI) schema requirements

**Source**: [Product Feed Spec](https://developers.openai.com/commerce/specs/feed)

**Delivery**: SFTP, file upload, or hosted URL. Formats: **jsonl.gz**, **csv.gz**. Refresh: **daily**.

### 2.1 Required fields (all products)

| Field | Type | Notes |
|-------|------|--------|
| `item_id` | string | Merchant product ID, max 100 chars, stable over time. |
| `title` | string | Max 150 chars; avoid all-caps. |
| `description` | string | Max 5,000 chars, plain text. |
| `url` | URL | Product detail page; HTTP 200, HTTPS preferred. |
| `image_url` | URL | Main product image; JPEG/PNG, HTTPS preferred. |
| `price` | number + currency | e.g. `79.99 USD`; ISO 4217. |
| `availability` | enum | `in_stock`, `out_of_stock`, `pre_order`, `backorder`, `unknown`. |
| `brand` | string | Max 70 chars. |
| `is_eligible_search` | boolean | Product can appear in ChatGPT search. |
| `is_eligible_checkout` | boolean | Direct purchase in ChatGPT; requires `is_eligible_search=true`. |
| `seller_name` | string | Max 70 chars. |
| `seller_url` | URL | HTTPS preferred. |
| `return_policy` | URL | HTTPS preferred. |
| `target_countries` | list | ISO 3166-1 alpha-2 (e.g. `["US"]`). |
| `store_country` | string | ISO 3166-1 alpha-2. |

### 2.2 Required when `is_eligible_checkout` is true

| Field | Type |
|-------|------|
| `seller_privacy_policy` | URL (HTTPS) |
| `seller_tos` | URL (HTTPS) |

### 2.3 Variants (if listing has variations)

| Field | Type |
|-------|------|
| `group_id` | string (max 70 chars) |
| `listing_has_variations` | boolean |

### 2.4 Optional but recommended

- Media: `additional_image_urls`, `video_url`, `model_3d_url`
- Item: `product_category`, `condition`, `material`, dimensions, weight, `age_group`
- Price: `sale_price`, `sale_price_start_date`, `sale_price_end_date`
- Availability: `availability_date`, `expiration_date`, `pickup_method`, `pickup_sla`
- Variants: `variant_dict`, `item_group_title`, `color`, `size`, `offer_id`
- Fulfillment: `shipping`, `is_digital`
- Merchant: `marketplace_seller`
- Returns: `accepts_returns`, `return_deadline_in_days`, `accepts_exchanges`
- Compliance: `warning`/`warning_url`, `age_restriction`
- Geo: `geo_price`, `geo_availability`

### 2.5 Prohibited Products Policy (ACP)

Products must **not** fall under: adult content, age-restricted (alcohol, nicotine, gambling), harmful/dangerous materials, weapons, prescription-only meds, unlicensed financial products, illegal or deceptive goods. See [spec](https://developers.openai.com/commerce/specs/feed).

---

## 3. UCP (Google) schema requirements

**Source**: [UCP Schema Reference](https://ucp.dev/specification/reference/) – **Item Response**, **Line Item Create/Update Request**

UCP does **not** define a full product feed document. It defines how a **product/item** is represented inside **checkout** and **order** payloads. Discovery is via `/.well-known/ucp` and business-defined catalog endpoints.

### 3.1 Item (product) in checkout/order – required

| Field | Type | Notes |
|-------|------|--------|
| `id` | string | **Required.** Must be recognized by Platform and Business; for Google must match the `id` in the product feed. |
| `title` | string | **Required.** Product title. |
| `price` | integer | **Required.** Unit price in **minor units** (cents). |

### 3.2 Item – optional

| Field | Type |
|-------|------|
| `image_url` | string (URI) |

### 3.3 Line item (quantity + item)

- `item`: Item Create Request `{ id }` or Item Response `{ id, title, price, image_url }`.
- `quantity`: integer, required.

So for **UCP**, the minimal compliant product has: **id**, **title**, **price** (in cents). **image_url** is optional but recommended.

---

## 4. Unified (canonical) product schema

A **single internal shape** can support both ACP and UCP by including at least:

| Field | Type | ACP | UCP | Notes |
|-------|------|-----|-----|--------|
| `id` / `item_id` | string | ✅ item_id | ✅ id | Stable ID. |
| `name` / `title` | string | ✅ title | ✅ title | |
| `description` | string | ✅ | — | UCP doesn’t require in Item. |
| `url` | string | ✅ | — | Product page. |
| `image_url` | string | ✅ | optional | |
| `price` | number | ✅ (major + currency) | ✅ (integer cents) | Store in major units + currency; convert to cents for UCP. |
| `currency` | string | ✅ (in price) | — | ISO 4217. |
| `availability` | string | ✅ enum | — | in_stock, out_of_stock, etc. |
| `brand` | string | ✅ | — | |
| `is_eligible_search` | boolean | ✅ | — | |
| `is_eligible_checkout` | boolean | ✅ | — | |
| `seller_name` | string | ✅ | — | Often partner-level. |
| `seller_url` | string | ✅ | — | |
| `return_policy` | string | ✅ | — | |
| `target_countries` | list | ✅ | — | |
| `store_country` | string | ✅ | — | |
| `seller_privacy_policy` | string | ✅ (if checkout) | — | |
| `seller_tos` | string | ✅ (if checkout) | — | |

**Unified minimum for “both compliant”**:  
`id`, `title`/`name`, `description`, `url`, `image_url`, `price`, `currency`, `availability`, `brand`, eligibility flags, seller/return/geo fields as above. For **UCP-only** flows, the minimum is `id`, `title`, `price` (and optionally `image_url`).

---

## 5. Our platform schema vs requirements

**Current `products` table** (and partner portal) columns:

| Column | ACP | UCP | Notes |
|--------|-----|-----|--------|
| `id` | ✅ item_id | ✅ id | |
| `name` | ✅ title | ✅ title | |
| `description` | ✅ | — | |
| `price` | ✅ | ✅ (convert to cents) | |
| `currency` | ✅ | — | |
| `image_url` | ✅ | optional | Present (migration). |
| `product_type`, `unit` | — | — | Portal-specific. |
| `is_available` | ⚠️ | — | Boolean; map to availability enum. |
| `capabilities`, `metadata` | — | — | Can store ACP/UCP extras. |
| `manifest_url` | — | — | Source manifest. |
| `embedding` | — | — | Semantic search. |

**Missing for full ACP**: `url`, `brand`, `is_eligible_search`, `is_eligible_checkout`, `seller_name`, `seller_url`, `return_policy`, `target_countries`, `store_country`, `seller_privacy_policy`, `seller_tos`. These can live in `metadata` or new columns and/or on `partners`.

**UCP**: Our schema already has `id`, `name`, `price`, `currency`, `image_url`. For UCP we only need to ensure **price** can be expressed in minor units (cents) when calling UCP APIs; no new columns strictly required for Item.

---

## 6. Validation in code

| Protocol | Module | Entry points |
|----------|--------|--------------|
| **ACP** | `protocols/acp_compliance.py` | `validate_product_acp()`, `filter_acp_compliant_products()`, `validate_acp_required_fields()`, `validate_acp_prohibited_content()`. |
| **UCP** | `protocols/ucp_compliance.py` | `validate_product_ucp()`, `filter_ucp_compliant_products()`, `validate_ucp_item_required_fields()`. Prohibited content reused from ACP. |

**Manifest ingest**: For ACP, use `validate_acp=true` on `POST /api/v1/admin/manifest/ingest` to cache only ACP-compliant products. For UCP feeds, you can run `validate_product_ucp()` or `filter_ucp_compliant_products()` before storing.

---

## 7. Summary

- **ACP**: Full product feed spec with many required fields (identifiers, title, description, url, image, price, availability, brand, eligibility, seller/return/geo, optional variant/fulfillment/compliance). Prohibited Products Policy applies.
- **UCP**: Product appears as **Item** in checkout/order: **id**, **title**, **price** (cents) required; **image_url** optional. No separate feed spec; catalog is defined by the business.
- **Unified**: A canonical product record that includes ACP’s required set also satisfies UCP’s Item requirements (with price conversion to cents for UCP). Our platform schema is missing several ACP-only fields; UCP Item is already covered except price-in-cents when exporting to UCP.
- **Validation**: Use `acp_compliance` for ACP feeds and “ChatGPT eligible” flows; use `ucp_compliance` for UCP/Google Item and catalog flows. Both can share the same prohibited-content policy.

For ACP-only details and validator usage, see [ACP_COMPLIANCE.md](./ACP_COMPLIANCE.md).

For **how AI platforms discover and use our products** (push feed vs expose API, and what to build for ChatGPT vs Google), see [AI_PLATFORM_PRODUCT_DISCOVERY.md](./AI_PLATFORM_PRODUCT_DISCOVERY.md).
