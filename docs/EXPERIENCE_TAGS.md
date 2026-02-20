# Experience tags (products)

Experience tags are thematic labels on products (e.g. `["luxury", "night out", "travel", "celebration"]`) used for **search and recommendations**. They are separate from **capability tags** (category/capability like `limo`, `flowers`, `dinner_reservation`).

## Schema

- **Table:** `products`
- **Column:** `experience_tags` — JSONB, default `[]`
- **Values:** Array of strings, lowercase, e.g. `["luxury", "night out", "travel", "celebration"]`
- **Index:** GIN on `experience_tags` for efficient containment queries

Migration: `supabase/migrations/20250128000036_products_experience_tags.sql`

## Partner portal

On the **Products** page, when editing a product, the **Experience tags** field is available. Partners enter comma-separated tags (e.g. `luxury, night out, travel, celebration`). The API normalizes to lowercase and stores up to 20 tags.

## Capability tags vs experience tags

| | capability_tags / capabilities | experience_tags |
|--|-------------------------------|------------------|
| **Purpose** | Category/capability (what the product is) | Thematic/experience (when/how it fits) |
| **Examples** | limo, flowers, dinner_reservation | luxury, night out, travel, celebration |
| **Storage** | `capability_tags` table + `product_capabilities` or `products.capabilities` JSONB | `products.experience_tags` JSONB |
| **Use** | Intent/discovery category matching, filters | Search/recommendations by theme or occasion |

Example: a Limo product might have `capabilities: ["limo"]` and `experience_tags: ["luxury", "night out", "travel", "celebration"]`.

## Using experience_tags in discovery

- **Discovery service** can select `experience_tags` when returning products and expose it in the API so orchestrator/chat can use it for ranking or filtering.
- **Semantic search** can include experience_tags in the text used for embedding or keyword match (e.g. user says “something fancy” → match products with `luxury` in `experience_tags`).
- **Recommendations** can filter or boost by experience_tags when the user’s intent or context implies a theme (e.g. “celebration” → include products with `celebration` in `experience_tags`).

Discovery today already returns product rows; adding `experience_tags` to the select and to the response payload is sufficient for downstream use. Future work can add filtering/boosting by experience_tags in the discovery aggregator or semantic search.
