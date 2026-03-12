"""
Dynamic Metadata Enricher (Phase 3: The Vibe Moat).

Intercepts products before ranking; enriches missing experience_tags via existing configured LLM.
For Shopify/external products: in-memory only (no DB write).

Single intercept path: All products (LocalDB, UCP, MCP, Shopify MCP) flow through scout_engine
which calls enrich_products_middleware after aggregator fetch and before ranking. No bypass.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Allowed tags for LLM to choose from (prevents hallucination)
ALLOWED_TAGS = [
    "luxury", "romantic", "baby", "celebration", "travel", "night_out", "family",
    "get_well", "thank_you", "graduation", "wedding", "anniversary", "birthday",
    "corporate", "adventure", "relaxation", "wellness", "gourmet",
]

_PROMPT = """Given the product descriptions below, assign 1-5 experience tags to each product.

Choose ONLY from these tags: """ + ", ".join(ALLOWED_TAGS) + """

Return a JSON object mapping index (0-based) to array of tags. Example:
{"0": ["luxury", "romantic"], "1": ["baby", "celebration"]}

Products (index: description):
"""


def _needs_enrichment(p: Dict[str, Any], source: str) -> bool:
    """True if product has no experience_tags and has description. Skip external-only (SHOPIFY) for DB write."""
    tags = p.get("experience_tags")
    if tags and isinstance(tags, list) and len(tags) > 0:
        return False
    desc = p.get("description") or p.get("name") or ""
    if not desc or not str(desc).strip():
        return False
    return True


def _parse_llm_tags_response(raw: str) -> Dict[int, List[str]]:
    """Parse LLM response into {index: [tags]}."""
    out: Dict[int, List[str]] = {}
    if not raw or not raw.strip():
        return out
    raw = raw.strip()
    if "```" in raw:
        raw = re.sub(r"```(?:json)?\s*", "", raw)
        raw = raw.split("```")[0].strip()
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return out
        tag_set = set(t.lower() for t in ALLOWED_TAGS)
        for k, v in parsed.items():
            try:
                idx = int(k)
            except (ValueError, TypeError):
                continue
            if isinstance(v, list):
                tags = [str(t).strip().lower() for t in v if t and str(t).strip() and str(t).strip().lower() in tag_set]
            elif isinstance(v, str):
                tags = [t.strip().lower() for t in v.split(",") if t.strip() and t.strip().lower() in tag_set]
            else:
                continue
            if tags:
                out[idx] = tags[:5]
    except json.JSONDecodeError:
        pass
    return out


async def _call_llm_for_tags(
    product_descriptions: List[str],
    llm_config: Dict[str, Any],
    provider: str,
    chat_client: Any,
) -> Dict[int, List[str]]:
    """Call LLM once with batched product descriptions. Returns {index: [tags]}."""
    if not product_descriptions or not chat_client:
        return {}
    body = "\n".join(f"{i}: {d[:500]}" for i, d in enumerate(product_descriptions))
    user_content = _PROMPT + body
    model = llm_config.get("model") or "gpt-4o"
    temperature = float(llm_config.get("temperature", 0.1))
    max_tokens = 300

    try:
        if provider in ("azure", "openrouter", "custom", "openai"):
            def _call():
                return chat_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Return only valid JSON. No markdown, no explanation."},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            response = await asyncio.to_thread(_call)
            raw = (response.choices[0].message.content or "").strip()
        elif provider == "gemini":
            gen_model = chat_client.GenerativeModel(model)

            def _call():
                return gen_model.generate_content(
                    user_content,
                    generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                )

            resp = await asyncio.to_thread(_call)
            raw = (getattr(resp, "text", None) or "").strip()
        else:
            return {}
        return _parse_llm_tags_response(raw)
    except Exception as e:
        logger.warning("Metadata enricher LLM call failed: %s", e)
        return {}


async def enrich_products(
    products: List[Dict[str, Any]],
    *,
    enabled: bool = True,
) -> List[Dict[str, Any]]:
    """
    Enrich products missing experience_tags using configured LLM.
    Mutates products in place. For external (SHOPIFY) source: in-memory only.
    Batch size: 5 products per LLM call.
    """
    if not enabled or not products:
        return products

    from db import get_supabase

    client = get_supabase()
    if not client:
        return products

    from packages.shared.platform_llm import get_platform_llm_config, get_llm_chat_client

    llm_config = get_platform_llm_config(client)
    if not llm_config or not llm_config.get("api_key"):
        return products

    provider, chat_client = get_llm_chat_client(llm_config)
    if not chat_client:
        return products

    # Collect indices and descriptions for products needing enrichment
    to_enrich: List[tuple[int, Dict[str, Any]]] = []
    for i, p in enumerate(products):
        meta = p.get("metadata") or {}
        source = str(meta.get("source", p.get("source", "DB"))).upper()
        if _needs_enrichment(p, source):
            desc = (p.get("description") or p.get("name") or "")[:500]
            to_enrich.append((i, p))

    if not to_enrich:
        return products

    batch_size = 5
    for start in range(0, len(to_enrich), batch_size):
        batch = to_enrich[start : start + batch_size]
        indices = [idx for idx, _ in batch]
        descriptions = [
            (p.get("description") or p.get("name") or "")[:500]
            for _, p in batch
        ]
        result = await _call_llm_for_tags(descriptions, llm_config, provider or "", chat_client)
        for rel_idx, (orig_idx, p) in enumerate(batch):
            tags = result.get(rel_idx, [])
            if tags:
                p["experience_tags"] = tags

    return products
