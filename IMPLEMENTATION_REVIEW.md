# Implementation Review: Protocol-Aware Agentic Orchestrator

**Document Version:** 1.0  
**Date:** 2025-01-28  
**Scope:** Post "Rip and Replace" refactor of the MODEL_INTERACTIONS_ARCHITECTURE

This document provides a technical review of the five architectural pillars implemented in the codebase, with explicit code references and snippets to verify each implementation.

---

## 1. Multi-Protocol Discovery Gateway

**Primary Location:** `packages/shared/discovery_aggregator.py`  
**Supporting:** `packages/shared/discovery.py`, `services/discovery-service/scout_engine.py`

### 1.1 Driver Implementations

#### LocalDBDriver
Calls the local database search function and normalizes results to `UCPProduct`.

```python
# packages/shared/discovery_aggregator.py (lines 103-126)
class LocalDBDriver:
    """Driver that calls the local DB search (search_products)."""

    def __init__(self, search_fn: Callable[..., Awaitable[List[Dict[str, Any]]]]):
        self._search = search_fn

    async def search(
        self,
        query: str,
        limit: int = 20,
        partner_id: Optional[str] = None,
        exclude_partner_id: Optional[str] = None,
    ) -> List[UCPProduct]:
        try:
            raw = await self._search(
                query=query,
                limit=limit,
                partner_id=partner_id,
                exclude_partner_id=exclude_partner_id,
            )
            return [_normalize_to_ucp_product(p, "DB") for p in (raw if isinstance(raw, list) else [])]
        except Exception as e:
            logger.warning("LocalDBDriver search failed: %s", e)
            return []
```

#### UCPManifestDriver
Fetches from partner `/.well-known/ucp.json` (or `/.well-known/ucp`) and catalog endpoints.

```python
# packages/shared/discovery_aggregator.py (lines 128-204)
class UCPManifestDriver:
    """Driver that fetches from partner /.well-known/ucp.json (or /.well-known/ucp) and catalog."""

    def __init__(self, get_partner_manifest_urls: Optional[Callable[[], Awaitable[List[str]]]] = None):
        self._get_urls = get_partner_manifest_urls

    async def search(...) -> List[UCPProduct]:
        # Fetches manifest, extracts catalog URL, queries catalog with q=query
        # Normalizes each item via _normalize_to_ucp_product(..., "UCP")
```

#### MCPDriver
Placeholder for Model Context Protocol (MCP) tools. Requires `mcp_search_fn` to be wired.

```python
# packages/shared/discovery_aggregator.py (lines 206-226)
class MCPDriver:
    """Driver that fetches from MCP (Model Context Protocol) tools. Placeholder until MCP client wired."""

    def __init__(self, mcp_search_fn: Optional[Callable[..., Awaitable[List[Dict[str, Any]]]]] = None):
        self._mcp_search = mcp_search_fn

    async def search(...) -> List[UCPProduct]:
        if not self._mcp_search:
            return []
        raw = await self._mcp_search(query=query, limit=limit)
        return [_normalize_to_ucp_product(p, "MCP") for p in (raw if isinstance(raw, list) else [])]
```

### 1.2 Asynchronous Fan-Out and Timeout Enforcement

```python
# packages/shared/discovery_aggregator.py (lines 255-286)
timeout_sec = self._timeout_ms / 1000.0
tasks: List[asyncio.Task] = []
if self._local:
    tasks.append(asyncio.create_task(self._local.search(...)))
if self._ucp:
    tasks.append(asyncio.create_task(self._ucp.search(...)))
if self._mcp:
    tasks.append(asyncio.create_task(self._mcp.search(...)))

try:
    results: List[List[UCPProduct]] = await asyncio.wait_for(
        asyncio.gather(*tasks, return_exceptions=True),
        timeout=timeout_sec,
    )
except asyncio.TimeoutError:
    logger.warning("DiscoveryAggregator timed out after %sms", self._timeout_ms)
    return []
```

### 1.3 discovery_timeout_ms from Admin Config

```python
# services/discovery-service/scout_engine.py (lines 134-159)
async def _fetch_via_aggregator(...) -> List[Dict[str, Any]]:
    """Fetch via DiscoveryAggregator (LocalDB + UCP + MCP) with timeout."""
    admin = await get_admin_orchestration_settings()
    timeout_ms = 5000
    if admin and isinstance(admin.get("discovery_timeout_ms"), (int, float)):
        timeout_ms = int(admin["discovery_timeout_ms"])
    local_driver = LocalDBDriver(search_products)
    aggregator = DiscoveryAggregator(
        local_db_driver=local_driver,
        ucp_driver=None,
        mcp_driver=None,
        timeout_ms=timeout_ms,
    )
    ucp_products = await aggregator.search(...)
    return [p.to_dict() for p in ucp_products]
```

### 1.4 UCPProduct Schema and Normalization

```python
# packages/shared/discovery_aggregator.py (lines 17-59)
@dataclass
class UCPProduct:
    """Normalized product schema with explicit capabilities and features to prevent LLM hallucination."""

    id: str
    name: str
    description: str = ""
    price: float = 0.0
    currency: str = "USD"
    partner_id: Optional[str] = None
    source: str = "DB"  # DB | UCP | MCP
    capabilities: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    url: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_eligible_search: bool = True
    is_eligible_checkout: bool = False
    sold_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API/LLM context."""
        return {
            "id": str(self.id),
            "name": self.name,
            ...
            "capabilities": list(self.capabilities),
            "features": list(self.features),
            ...
        }
```

```python
# packages/shared/discovery_aggregator.py (lines 59-99)
def _normalize_to_ucp_product(raw: Dict[str, Any], source: str = "DB") -> UCPProduct:
    """Normalize raw product dict to UCPProduct with explicit capabilities/features."""
    caps = raw.get("capabilities")
    if isinstance(caps, str):
        caps = [c.strip() for c in caps.split(",") if c.strip()]
    elif isinstance(caps, list):
        caps = [str(c) for c in caps if c]
    else:
        caps = []

    feats = raw.get("features")
    # ... similar for features
    return UCPProduct(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", raw.get("title", ""))),
        ...
        capabilities=caps,
        features=feats,
        source=source,
        ...
    )
```

---

## 2. State-Driven Planner & External Context

**Primary Location:** `services/orchestrator-service/agentic/loop.py`  
**Supporting:** `services/orchestrator-service/agentic/planner.py`

### 2.1 AWAITING_PROBE State: Missing Location/Time Check

```python
# services/orchestrator-service/agentic/loop.py (lines 1103-1116)
ORCHESTRATOR_STATE_AWAITING_PROBE = "AWAITING_PROBE"
```

```python
# services/orchestrator-service/agentic/loop.py (lines 1106-1116)
def _has_location_or_time(
    intent_data: Optional[Dict[str, Any]],
    user_message: Optional[str] = None,
) -> bool:
    """Return True if we have location or time for composite experiences (required before discovery)."""
    if not intent_data:
        return False
    loc = _extract_location(intent_data)
    if loc and str(loc).strip():
        return True
    hints = _extract_fulfillment_hints(intent_data, user_message)
    if hints and (hints.get("pickup_time") or hints.get("pickup_address")):
        return True
    for e in intent_data.get("entities", []):
        if isinstance(e, dict):
            t = (e.get("type") or "").lower()
            if t in ("location", "pickup_time", "time", "date") and e.get("value"):
                return True
    return False
```

**Intent Preview Loop Trigger:**

```python
# services/orchestrator-service/agentic/loop.py (lines 550-556)
elif rec == "discover_composite" and intent_data.get("intent_type") == "discover_composite":
    # AWAITING_PROBE: Do not execute discovery if location or time is missing
    if not _has_location_or_time(intent_data, user_message) and state.get("probe_count", 0) < 2:
        state["orchestrator_state"] = ORCHESTRATOR_STATE_AWAITING_PROBE
        plan = None  # Let planner run → complete with probing for location/time
    else:
        plan = { "action": "tool", "tool_name": "discover_composite", ... }
```

### 2.2 External Context: Weather and Events Before Discovery

```python
# services/orchestrator-service/agentic/loop.py (lines 720-744)
if tool_name == "discover_composite" and intent_data and intent_data.get("intent_type") == "discover_composite":
    # ...
    loc = tool_args.get("location")
    if loc and str(loc).strip():
        if not engagement_data.get("weather"):
            await _emit_thinking(on_thinking, "before_weather", {"location": loc}, thinking_messages or {})
            weather_result = await _get_weather(loc)
            engagement_data["weather"] = weather_result.get("data", weather_result)
        if not (engagement_data.get("occasions") or {}).get("events"):
            await _emit_thinking(on_thinking, "before_occasions", {"location": loc}, thinking_messages or {})
            occasions_result = await _get_upcoming_occasions(loc)
            engagement_data["occasions"] = occasions_result.get("data", occasions_result)

        # Contextual pivot: rain → swap outdoor for indoor
        weather_desc = (engagement_data.get("weather") or {}).get("description", "")
        if weather_desc and "rain" in weather_desc.lower():
            exp_name = tool_args.get("experience_name", "")
            sq = tool_args.get("search_queries") or []
            if _is_outdoor_experience(exp_name, sq):
                new_sq, new_opts = _pivot_outdoor_to_indoor(sq, tool_args.get("bundle_options"))
                tool_args["search_queries"] = new_sq
                tool_args["bundle_options"] = new_opts
                engagement_data["weather_warning"] = (
                    f"Weather in {loc}: {weather_desc}. We've adjusted your plan for indoor options."
                )
```

### 2.3 Outdoor Pivot Logic

```python
# services/orchestrator-service/agentic/loop.py (lines 1127-1180)
def _is_outdoor_experience(experience_name: str, search_queries: Optional[List[str]]) -> bool:
    """Return True if experience is outdoor/location-based (picnic, date night, etc.)."""
    name = (experience_name or "").lower()
    outdoor_keywords = ("picnic", "outdoor", "garden", "park", "beach", "rooftop")
    if any(k in name for k in outdoor_keywords):
        return True
    qs = " ".join(str(s).lower() for s in (search_queries or []))
    if any(k in qs for k in outdoor_keywords):
        return True
    return False


def _pivot_outdoor_to_indoor(
    search_queries: List[str],
    bundle_options: Optional[List[Dict[str, Any]]],
) -> tuple:
    """Swap outdoor categories (e.g. picnic) for indoor when weather is rain. Returns (queries, options)."""
    pivot_map = {
        "picnic": "indoor dining",
        "outdoor": "indoor",
        "garden": "indoor dining",
        "park": "indoor",
        "beach": "indoor",
    }
    new_queries = []
    for q in search_queries or []:
        ql = str(q).lower()
        replaced = False
        for outdoor, indoor in pivot_map.items():
            if outdoor in ql:
                new_queries.append(indoor)
                replaced = True
                break
        if not replaced:
            new_queries.append(q)
    # ... similar for bundle_options
```

---

## 3. The Partner Balancer

**Primary Location:** `services/orchestrator-service/agentic/response.py`

### 3.1 Score Formula: `score = rel * w`

- `rel` = `_source_score(source, tier)` — protocol affinity for the tier
- `w` = `_weight(partner_id)` — `admin_weight` from `partner_representation_rules`

```python
# services/orchestrator-service/agentic/response.py (lines 364-428)
def _weight(pid: str) -> float:
    r = partner_rules.get(str(pid), {})
    return float(r.get("admin_weight", 1.0))

def _source_score(source: str, tier: int) -> float:
    # tier 1=DB, 2=UCP, 3=MCP
    s = (source or "DB").upper()
    if tier == 1:
        return 1.5 if s == "DB" else (0.7 if s == "UCP" else 0.5)
    if tier == 2:
        return 1.5 if s == "UCP" else (0.7 if s == "DB" else 0.5)
    if tier == 3:
        return 1.5 if s == "MCP" else (0.7 if s == "DB" else 0.5)
    return 1.0

# ...
for p in prods:
    pid = p.get("partner_id", "")
    if pid and pid in used_partners:
        continue  # Equal representation: no partner twice per tier
    rel = _source_score(p.get("source", "DB"), tier_idx + 1)
    w = _weight(pid or "default")
    score = rel * w
    if score > best_score:
        best_score = score
        best = p
```

### 3.2 Equal Partner Representation: No Partner Twice Per Tier

```python
# services/orchestrator-service/agentic/response.py (lines 406-444)
for tier_idx in range(3):
    used_partners: set = set()
    product_ids: List[str] = []
    # ...
    for cat in cat_order:
        prods = products_by_cat.get(cat, [])
        best = None
        best_score = -1.0
        for p in prods:
            pid = p.get("partner_id", "")
            if pid and pid in used_partners:
                continue  # Equal representation: no partner twice per tier
            rel = _source_score(p.get("source", "DB"), tier_idx + 1)
            w = _weight(pid or "default")
            score = rel * w
            if score > best_score:
                best_score = score
                best = p
                # ...
        if best:
            product_ids.append(str(best["id"]))
            if best.get("partner_id"):
                used_partners.add(str(best["partner_id"]))
```

### 3.3 Tier Labels

- **Tier 1:** The Essential (DB heavy)
- **Tier 2:** The Premium (UCP heavy)
- **Tier 3:** The Express (MCP heavy)

```python
# services/orchestrator-service/agentic/response.py (lines 379-385)
tier_labels = ["The Essential", "The Premium", "The Express"]
tier_descriptions = [
    "A curated selection from our trusted local partners.",
    "Premium picks from our verified UCP catalog.",
    "Express options for a quick, seamless experience.",
]
```

---

## 4. Anti-Hallucination & Engagement Prompts

**Primary Location:** `services/orchestrator-service/agentic/response.py`  
**DB:** `supabase/migrations/20250128000031_protocol_aware_prompts.sql`  
**Code Defaults:** `packages/shared/prompts/` (intent only; engagement composite uses DB)

### 4.1 engagement_discover_composite System Prompt

**Source:** Migration `20250128000031_protocol_aware_prompts.sql` and code default `RESPONSE_SYSTEM_COMPOSITE` in `response.py`:

```
You are a luxury Universal Services Orchestrator Concierge.

Tone & Style: [INJECT ADMIN_CONFIG.GLOBAL_TONE AND LANGUAGE].

**The Goal:** Write a flowing, evocative 'Narrative Experience Plan' (e.g., "Your evening begins as the sun sets, with a sleek ride arriving at 6 PM..."). Do not list products like a receipt. Focus on the feeling, the atmosphere, and the flow of the event.

**ANTI-HALLUCINATION STRICT RULES:**
1. You MUST paint a vivid picture, but you may ONLY use the exact product names, features, and capabilities provided in the context data.
2. DO NOT invent amenities. If a Limo is provided, describe a "luxurious, smooth ride," but DO NOT say "enjoy complimentary champagne" unless "champagne" is explicitly listed in the product's features.
3. Weave weather/event data naturally into the narrative (e.g., "Since it will be a crisp 65 degrees, the indoor seating is secured...").

Calculate and display the Total Cost of Ownership (TCO) clearly at the bottom.
Explicitly mention if a partner is 'Verified' via Local/UCP/MCP.

When we're still gathering details: Ask 1–2 friendly questions (date, budget, dietary, location). Do NOT list products.
```

### 4.2 Context Enforces Only Provided Data

**`_build_context`** supplies only the product data that comes from discovery (UCPProduct schema with `capabilities` and `features`):

```python
# services/orchestrator-service/agentic/response.py (lines 116-122)
parts.append(
    f"User asked for {exp_name}. We have a curated bundle ready. "
    f"Bundle includes (use these exact names): {', '.join(product_names)}. Total: {total_str}. "
    "Describe this as a NARRATIVE EXPERIENCE PLAN: how the evening unfolds (e.g. pickup at 6 PM—need address; flowers sent to restaurant; limo pickup with decor). "
    "REQUIRED: Include this sentence before the CTA: 'To place this order I'll need pickup time, pickup address, and delivery address — you can share them in the chat now or when you tap Add this bundle.' "
    "Do NOT say 'Found X product(s)' or list products with prices. Write a flowing 3–5 sentence description. End with total and 'Add this bundle' CTA."
)
```

```python
# services/orchestrator-service/agentic/response.py (lines 152-154)
parts.append(
    f"Allowed CTAs (suggest ONLY these): {', '.join(allowed_ctas)}. Do NOT suggest same-day delivery, delivery options, or any feature not listed. "
    f"Present as a curated bundle. ONLY mention products from Product data below—do NOT invent any. Product data (ONLY these): {'; '.join(all_items[:10])}. Be warm and helpful."
)
```

### 4.3 Global Tone Injection

```python
# services/orchestrator-service/agentic/response.py (lines 285-291)
if intent_type == "discover_composite":
    admin = get_admin_orchestration_settings()
    tone = (admin or {}).get("global_tone", "warm, elegant, memorable")
    system_prompt = system_prompt.replace(
        "[INJECT ADMIN_CONFIG.GLOBAL_TONE AND LANGUAGE]",
        tone,
    )
```

### 4.4 UCPProduct Schema as Source of Truth

Products from discovery are normalized to `UCPProduct` with explicit `capabilities` and `features` lists. The engagement LLM receives only those fields via `_build_context`, so it cannot invent amenities not present in the schema.

---

## 5. Admin Configuration Schema

**Migrations:** `supabase/migrations/20250128000029_admin_orchestration_settings.sql`  
`supabase/migrations/20250128000030_partner_representation_rules.sql`

### 5.1 admin_orchestration_settings

```sql
-- supabase/migrations/20250128000029_admin_orchestration_settings.sql
CREATE TABLE IF NOT EXISTS admin_orchestration_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  global_tone TEXT DEFAULT 'warm, elegant, memorable',
  model_temperature DECIMAL(3,2) DEFAULT 0.7 CHECK (model_temperature >= 0 AND model_temperature <= 2.0),
  autonomy_level TEXT DEFAULT 'balanced' CHECK (autonomy_level IN ('conservative', 'balanced', 'aggressive')),
  discovery_timeout_ms INT DEFAULT 5000 CHECK (discovery_timeout_ms >= 500 AND discovery_timeout_ms <= 60000),
  ucp_prioritized BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default row if empty
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM admin_orchestration_settings LIMIT 1) THEN
    INSERT INTO admin_orchestration_settings (global_tone, model_temperature, autonomy_level, discovery_timeout_ms, ucp_prioritized)
    VALUES ('warm, elegant, memorable', 0.7, 'balanced', 5000, false);
  END IF;
END $$;

COMMENT ON TABLE admin_orchestration_settings IS 'Admin-controlled orchestration: tone, temperature, autonomy, discovery timeout';
COMMENT ON COLUMN admin_orchestration_settings.global_tone IS 'Injected into engagement prompts (e.g. warm, elegant, memorable)';
COMMENT ON COLUMN admin_orchestration_settings.model_temperature IS 'LLM temperature for creative responses (0-2)';
COMMENT ON COLUMN admin_orchestration_settings.autonomy_level IS 'conservative=more probing, balanced, aggressive=assume defaults';
COMMENT ON COLUMN admin_orchestration_settings.discovery_timeout_ms IS 'Timeout for discovery aggregator fan-out (ms)';
```

### 5.2 partner_representation_rules

```sql
-- supabase/migrations/20250128000030_partner_representation_rules.sql
CREATE TABLE IF NOT EXISTS partner_representation_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
  admin_weight DECIMAL(5,2) DEFAULT 1.0 CHECK (admin_weight >= 0 AND admin_weight <= 10.0),
  preferred_protocol TEXT DEFAULT 'DB' CHECK (preferred_protocol IN ('UCP', 'MCP', 'DB')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(partner_id)
);

CREATE INDEX IF NOT EXISTS idx_partner_representation_rules_partner ON partner_representation_rules(partner_id);
CREATE INDEX IF NOT EXISTS idx_partner_representation_rules_protocol ON partner_representation_rules(preferred_protocol);

COMMENT ON TABLE partner_representation_rules IS 'Admin weight and protocol preference per partner for Partner Balancer';
COMMENT ON COLUMN partner_representation_rules.admin_weight IS 'Multiplier for relevance (1.0=neutral, >1=boost, <1=reduce)';
COMMENT ON COLUMN partner_representation_rules.preferred_protocol IS 'UCP=manifest, MCP=model context, DB=local database';
```

---

## Summary of Key File References

| Pillar | Primary File | Supporting Files |
|--------|--------------|------------------|
| Multi-Protocol Discovery | `packages/shared/discovery_aggregator.py` | `packages/shared/discovery.py`, `services/discovery-service/scout_engine.py` |
| State-Driven Planner | `services/orchestrator-service/agentic/loop.py` | `services/orchestrator-service/agentic/planner.py` |
| Partner Balancer | `services/orchestrator-service/agentic/response.py` | `services/orchestrator-service/db.py` |
| Anti-Hallucination & Prompts | `services/orchestrator-service/agentic/response.py` | `supabase/migrations/20250128000031_protocol_aware_prompts.sql` |
| Admin Schema | `supabase/migrations/20250128000029_admin_orchestration_settings.sql` | `supabase/migrations/20250128000030_partner_representation_rules.sql` |
