"""Azure OpenAI integration for intent resolution (Module 4)."""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from openai import AzureOpenAI

from config import settings

INTENT_SYSTEM_PROMPT = """You are an intent resolver for a multi-vendor order platform. Extract structured intent from user messages.

Intent types: discover, add_to_bundle, checkout, track_status, support, customize, unknown

Entities to extract when present: product_type, location, quantity, price_range, date, partner_name

For discover intent, search_query must be a product category or keyword (flowers, chocolates, limo, gifts, cakes, etc.).
- Extract the product/service the user wants, not the action verb. "find limo service" -> "limo", "get flowers" -> "flowers".
- If the user asks for "sample products", "demo", "show me some", "brief summary", "anything", "what products do you have", "what do you have", or similar without a specific product: use "browse" as search_query (Discovery will return sample products).
- Never use filler words or verbs (please, hi, hello, find, get, search) as search_query; use "browse" for generic requests.
- Normalize to a product category: "send flowers to mom" -> "flowers", "I want something sweet" -> "chocolates", "find limo service" -> "limo".

Respond with valid JSON only, no markdown or extra text. Format:
{
  "intent_type": "<one of the intent types>",
  "entities": [
    {"type": "<entity_type>", "value": "<extracted_value>", "confidence": 0.0-1.0}
  ],
  "confidence_score": 0.0-1.0,
  "search_query": "<product category or 'browse' for sample/demo>"
}"""


def get_client() -> Optional[AzureOpenAI]:
    """Get Azure OpenAI client if configured."""
    if not settings.azure_openai_configured:
        return None
    return AzureOpenAI(
        api_key=settings.azure_openai_api_key,
        api_version="2024-02-01",
        azure_endpoint=settings.azure_openai_endpoint.rstrip("/"),
    )


async def resolve_intent(text: str) -> Dict[str, Any]:
    """
    Call Azure OpenAI to resolve intent from natural language.
    Returns dict with intent_type, entities, confidence_score, search_query.
    """
    client = get_client()
    if not client:
        return _fallback_resolve(text)

    try:
        response = await asyncio.to_thread(
            lambda: client.chat.completions.create(
                model=settings.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=500,
            )
        )
        content = response.choices[0].message.content or "{}"
        return _parse_llm_response(content, text)
    except Exception:
        return _fallback_resolve(text)


def _parse_llm_response(content: str, original_text: str) -> Dict[str, Any]:
    """Parse LLM JSON response, with fallback."""
    content = content.strip()
    # Remove markdown code blocks if present
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        data = json.loads(content)
        raw_query = (data.get("search_query") or "").strip()
        # If LLM returned a generic or action word, use fallback extraction; "browse" passes through
        if raw_query.lower() in _GENERIC_QUERY_WORDS or raw_query.lower() in _ACTION_SKIP or (len(raw_query) < 4 and raw_query.lower() != "browse"):
            raw_query = _extract_search_query(original_text)
        else:
            raw_query = raw_query or _extract_search_query(original_text)
        return {
            "intent_type": data.get("intent_type", "discover"),
            "entities": data.get("entities", []),
            "confidence_score": float(data.get("confidence_score", 0.8)),
            "search_query": raw_query or "browse",
        }
    except json.JSONDecodeError:
        return _fallback_resolve(original_text)


# Product keywords for fallback search_query extraction (discover intent)
_PRODUCT_KEYWORDS = [
    "flowers", "chocolates", "chocolate", "gifts", "gift", "cakes", "cake",
    "bouquet", "plants", "candy", "candies", "wine", "spa", "massage",
    "products", "items",
]

# Generic words → Discovery treats as browse (returns sample products)
_GENERIC_QUERY_WORDS = {"please", "hi", "hello", "hey", "sample", "demo", "anything", "something", "show", "return", "brief", "small", "set", "browse", "intent", "example", "examples", "what"}

# Action verbs to skip when extracting product (e.g. "find limo service" -> "limo")
_ACTION_SKIP = {"find", "search", "get", "need", "looking", "show", "want", "send"}

def _extract_search_query(text: str) -> str:
    """Extract product keyword from text for discovery search."""
    text_lower = text.strip().lower()
    if not text_lower:
        return "browse"
    # Sample/demo requests → browse (Discovery returns products without filter)
    if any(w in text_lower for w in ["sample", "demo", "show me some", "brief", "anything", "something", "example", "examples"]):
        return "browse"
    # "what do you have" / "what products" / "what's available" → browse
    if any(w in text_lower for w in ["what products", "what do you have", "what's available", "what do you sell"]):
        return "browse"
    # Check for known product keywords
    for kw in _PRODUCT_KEYWORDS:
        if kw in text_lower:
            return kw
    # Extract word before "to" or "for" (e.g. "send flowers to mom" -> "flowers")
    for prep in [" to ", " for ", " about "]:
        if prep in text_lower:
            parts = text_lower.split(prep, 1)
            words = parts[0].split()
            skip = {"i", "want", "send", "looking", "find", "get", "need", "a", "an", "the"}
            for w in reversed(words):
                clean = re.sub(r"[^\w]", "", w)
                if len(clean) > 2 and clean not in skip and clean not in _GENERIC_QUERY_WORDS:
                    return clean
    # Fallback: first content word longer than 3 chars (skip action verbs)
    words = re.findall(r"\b\w{4,}\b", text_lower)
    for w in (words or []):
        if w not in _GENERIC_QUERY_WORDS and w not in _ACTION_SKIP:
            return w
    return "browse"


def _fallback_resolve(text: str) -> Dict[str, Any]:
    """Fallback when Azure OpenAI is not configured or fails."""
    text_lower = text.strip().lower()
    # Simple heuristics
    if any(w in text_lower for w in ["track", "status", "where is", "delivery"]):
        intent_type = "track_status"
    elif any(w in text_lower for w in ["checkout", "pay", "order", "buy"]):
        intent_type = "checkout"
    elif any(w in text_lower for w in ["help", "support", "problem"]):
        intent_type = "support"
    elif any(w in text_lower for w in ["add", "cart", "bundle"]):
        intent_type = "add_to_bundle"
    else:
        intent_type = "discover"

    search_query = _extract_search_query(text) if intent_type == "discover" else text.strip()[:100]

    return {
        "intent_type": intent_type,
        "entities": [],
        "confidence_score": 0.6,
        "search_query": search_query or "browse",
    }
