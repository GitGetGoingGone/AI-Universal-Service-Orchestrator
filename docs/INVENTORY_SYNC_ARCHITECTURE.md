# Inventory Sync Architecture

Pillar 1: Partner inventory sync (webhook vs poll). Schema: `product_inventory` table.

## Overview

Product inventory is synced from partner systems into `product_inventory`. Each product has one row with `quantity`, `reserved_quantity`, `sync_method`, and `last_synced_at`.

## Sync Methods

| Method | Description | Partner config |
|--------|-------------|----------------|
| `webhook` | Partner pushes updates via `POST /webhooks/inventory` | X-Webhook-Secret, callback URL |
| `poll` | Platform polls partner API on schedule | poll_url, poll_interval_min |

## Webhook Schema

`POST /webhooks/inventory` (Discovery service):

```json
{
  "product_id": "uuid",
  "partner_id": "uuid",
  "event": "stock_change",
  "previous_value": 10,
  "new_value": 5,
  "thread_ids": ["chatgpt-thread-1"]
}
```

Events: `stock_change`, `price_change`, `availability_change`.

## Product Inventory Table

| Column | Type | Description |
|--------|------|-------------|
| product_id | UUID | FK to products |
| partner_id | UUID | FK to partners |
| quantity | INTEGER | Available stock |
| reserved_quantity | INTEGER | Reserved for pending orders |
| sync_method | VARCHAR | webhook \| poll |
| last_synced_at | TIMESTAMPTZ | Last sync timestamp |
| source_system | TEXT | Partner system identifier |

## Capability Mapping

`capability_tags` → product capabilities. Products can have `capabilities` JSONB and `product_capabilities` junction. Search filters use capability tags for relevance.

Mapping: `capability_tags.tag_name` → `product_capabilities.capability_tag` → product filters in Scout Engine.
