# ACP (OpenAI Product Feed) Compliance

This doc describes how the platform aligns with the [OpenAI Product Feed Spec](https://developers.openai.com/commerce/specs/feed) and how we ensure products are compliant.

**Unified ACP + UCP schema**: For a single reference that covers both OpenAI ACP and Google UCP product/item requirements, see [COMMERCE_FEED_SCHEMA_REQUIREMENTS.md](./COMMERCE_FEED_SCHEMA_REQUIREMENTS.md).

---

## 1. Spec summary (reference)

- **Source**: [Product Feed Spec](https://developers.openai.com/commerce/specs/feed) – how merchants share product data with OpenAI for ChatGPT search and checkout.
- **Delivery**: Merchants push feeds via **SFTP**, **file upload**, or **hosted URL**. Formats: **jsonl.gz**, **csv.gz** (gzip-compressed). Refresh: **daily**.
- **Required fields** (abbreviated):  
  `is_eligible_search`, `is_eligible_checkout`, `item_id`, `title`, `description`, `url`, `brand`, `image_url`, `price`, `availability`, `seller_name`, `seller_url`, `return_policy`, `target_countries`, `store_country`.  
  If `is_eligible_checkout` is true: also `seller_privacy_policy`, `seller_tos`.  
  Variants: `group_id`, `listing_has_variations`.
- **Prohibited Products Policy**: No adult content, age-restricted (alcohol, nicotine, gambling), harmful/dangerous materials, weapons, prescription-only meds, unlicensed financial products, illegal or deceptive goods. Merchants are responsible for compliance; OpenAI may remove products or ban sellers.

---

## 2. How we ensure compliance

### 2.1 ACP compliance validator

We validate product records against the spec in code:

- **Module**: `services/discovery-service/protocols/acp_compliance.py`
- **Checks**:
  - **Required fields**: Ensures all ACP-required fields are present and non-empty (with optional checkout and variant requirements).
  - **Prohibited content**: Keyword/category blocklist derived from the Prohibited Products Policy (e.g. adult, alcohol, nicotine, weapons, prescription, etc.). Runs over title, description, category, brand.

**Functions:**

| Function | Purpose |
|----------|---------|
| `validate_acp_required_fields(product, ...)` | Returns list of **missing** required field names. |
| `validate_acp_prohibited_content(product)` | Returns list of **prohibited** violation descriptions. |
| `validate_product_acp(product, ...)` | Returns `(is_compliant, missing_fields, prohibited_violations)`. |
| `filter_acp_compliant_products(products, ...)` | Splits a list into compliant vs non-compliant and attaches `_acp_errors` to non-compliant items. |

Use these when:

- **Ingesting ACP feeds**: After parsing with `parse_acp_feed()`, run `validate_product_acp()` (or `filter_acp_compliant_products()`) and only store or surface compliant products, or store with a compliance flag.
- **Partner portal**: Before marking a product as “eligible for ChatGPT” or before exporting a feed, run `validate_product_acp()` and show missing fields / prohibited violations in the UI.
- **Export for OpenAI**: When building a feed for ChatGPT (jsonl.gz/csv.gz), only include products that pass `validate_product_acp()` and optionally re-validate prohibited content.

### 2.2 Where validation runs today

- **ACP adapter** (`protocols/acp_adapter.py`): Parses incoming feeds into a unified shape; it does **not** run the compliance validator by default. Callers (e.g. manifest ingest or an export pipeline) should call `acp_compliance.validate_product_acp()` or `filter_acp_compliant_products()`.
- **Manifest ingest** (`manifest_cache.cache_partner_manifest`): Does **not** yet run ACP validation. You can add a step after `parse_acp_feed()` to filter or flag non-compliant products using `filter_acp_compliant_products()`.
- **Partner portal**: Products are created with `name`, `description`, `price`, etc. There is **no** ACP validation in the portal yet. To ensure only ACP-compliant products are eligible for ChatGPT, add validation (and optional UI) using `acp_compliance` before saving or before marking “ACP eligible.”

### 2.3 Optional: enforce on ingest

To only cache ACP-compliant products from manifest ingest:

1. In `manifest_cache.cache_partner_manifest()`, after `parse_acp_feed()` (for `manifest_type="acp"`), call `filter_acp_compliant_products(products, strict=True)`.
2. Store only the compliant list in `partner_manifests.manifest_data`, and optionally log or return the non-compliant list with `_acp_errors` for partner feedback.

---

## 3. Gaps: our schema vs ACP spec

Our **products** table (and partner portal) do not store all ACP-required fields. So “ensuring compliance” means either (a) validating only what we have and accepting that we cannot be fully compliant until we add fields, or (b) adding fields and then validating.

| ACP required field | In our products table / portal? | Notes |
|--------------------|----------------------------------|--------|
| item_id            | ✅ `id`                          | UUID; ACP allows string ID. |
| title              | ✅ `name`                        | |
| description        | ✅ `description`                 | |
| url                | ❌                               | Product detail page URL. Can go in `metadata` or new column. |
| image_url          | ✅ (column added in migration)   | |
| price              | ✅ `price` + `currency`          | |
| availability       | ⚠️ `is_available` (boolean)      | ACP expects enum: in_stock, out_of_stock, etc. Map as needed. |
| brand              | ❌                               | Can go in `metadata` or new column. |
| is_eligible_search  | ❌                               | Can go in `metadata` or new column. |
| is_eligible_checkout| ❌                               | Can go in `metadata` or new column. |
| seller_name        | ❌                               | Partner-level; could come from `partners.business_name`. |
| seller_url         | ❌                               | Partner-level. |
| return_policy       | ❌                               | Partner or product level. |
| target_countries   | ❌                               | e.g. in `metadata` or new column. |
| store_country      | ❌                               | Partner-level. |
| seller_privacy_policy, seller_tos | ❌ | Required if checkout eligible. |

So today we **cannot** claim full ACP compliance for products created only in the portal, because we don’t store url, brand, seller_*, return_policy, target_countries, store_country, or eligibility flags. The **validator** will report these as missing when you run it. To fully ensure compliance:

1. **Extend schema**: Add columns or `metadata` keys for missing ACP fields (url, brand, is_eligible_search, is_eligible_checkout, target_countries, store_country, return_policy, seller_privacy_policy, seller_tos), and source seller_name/seller_url from `partners`.
2. **Use the validator**: On ingest (ACP feeds), in the portal before “ACP eligible,” and when building an export feed, call `validate_product_acp()` / `filter_acp_compliant_products()` and only allow compliant products to be used for ChatGPT-facing flows.
3. **Export format**: When publishing a feed to OpenAI, output **jsonl.gz** or **csv.gz** per the [Integration Overview](https://developers.openai.com/commerce/specs/feed) and only include products that pass the validator.

---

## 4. Prohibited Products Policy

The validator in `acp_compliance.py` implements a **keyword/category blocklist** inspired by the spec’s Prohibited Products Policy. It is not a full legal/compliance engine. You should:

- Treat it as a **first-line check** to catch obviously prohibited categories (adult, alcohol, nicotine, weapons, prescription, etc.).
- Rely on **merchant responsibility** and **human review** for edge cases and legal compliance.
- Adjust `ACP_PROHIBITED_CATEGORIES` and `ACP_PROHIBITED_KEYWORDS` as needed for your policy and jurisdiction.

---

## 5. Summary

- **How we ensure compliance**: We provide an **ACP compliance validator** (`protocols/acp_compliance.py`) that checks **required fields** and **prohibited content** per the [Product Feed Spec](https://developers.openai.com/commerce/specs/feed). Use it on **ingest**, in the **partner portal** (e.g. before “ACP eligible”), and when **exporting** a feed for OpenAI.
- **Current limitation**: Our DB and portal do not yet store all ACP-required fields (url, brand, seller_*, return_policy, target_countries, store_country, eligibility flags). Until those are added and populated, the validator will report missing fields; only products that have or inherit these fields (e.g. from an ACP feed) can be fully compliant.
- **Prohibited content**: Enforced via a blocklist in code; supplement with merchant policies and human review.
