# Capability Mapping

Pillar 1: capability_tags → product capabilities, search filters.

## Schema

- `capability_tags`: id, tag_name, tag_category, description, parent_tag_id
- `product_capabilities`: product_id, capability_tag (junction)
- `products.capabilities`: JSONB for free-form capabilities

## Mapping

| capability_tags | product_capabilities | Scout search |
|-----------------|---------------------|--------------|
| tag_name | capability_tag | Filter by tag |
| tag_category | - | Category filter |
| parent_tag_id | - | Hierarchy |

## Search Filters

Scout Engine uses capability tags when:
- `?capability=floral` filters products with capability_tag 'floral'
- `?occasion=birthday` maps to capability tags (beads/bridge logic in UCP)
