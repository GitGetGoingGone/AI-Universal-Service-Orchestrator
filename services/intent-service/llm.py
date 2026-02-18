"""Intent resolution via LLM (Platform Config) or heuristics fallback."""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from packages.shared.discovery import derive_search_query
from packages.shared.prompts import get_intent_system_prompt

logger = logging.getLogger(__name__)


async def resolve_intent(
    text: str,
    user_id: Optional[str] = None,
    last_suggestion: Optional[str] = None,
    force_model: bool = False,
) -> Dict[str, Any]:
    """
    Resolve intent from natural language. Uses LLM when Platform Config is set; else heuristics.
    """
    if not text or not text.strip():
        return {
            "intent_type": "browse",
            "search_query": "",
            "entities": [],
            "confidence_score": 0.5,
        }

    from db import get_supabase
    from packages.shared.platform_llm import get_platform_llm_config, get_model_interaction_prompt, get_llm_chat_client

    supabase = get_supabase()
    llm_config = get_platform_llm_config(supabase) if supabase else None
    prompt_cfg = get_model_interaction_prompt(supabase, "intent") if supabase else None

    if not supabase:
        logger.info("Intent: Supabase not configured, using heuristics")
    elif not llm_config:
        logger.info("Intent: No LLM config (active_llm_provider_id not set or provider missing), using heuristics")
    elif not llm_config.get("api_key"):
        logger.info("Intent: LLM config has no api_key (decryption failed or key not stored), using heuristics")
    elif prompt_cfg is not None and not prompt_cfg.get("enabled", True):
        logger.info("Intent: Intent prompt disabled in Model Interactions, using heuristics")

    # Single source: DB (model_interaction_prompts) overrides; else packages/shared/prompts/intent_system.txt
    system_prompt = (prompt_cfg.get("system_prompt") if prompt_cfg else None) or get_intent_system_prompt()
    if not system_prompt or not system_prompt.strip():
        logger.warning("Intent: No prompt from DB or file; using minimal fallback. Configure model_interaction_prompts or ensure packages/shared/prompts/intent_system.txt exists.")
        system_prompt = (
            'You are an intent classifier. Return JSON: {"intent_type":"discover|checkout|track|support|browse","search_query":"","entities":[],"confidence_score":0.7}. '
            "Use discover_composite for date night, birthday party, picnic."
        )
    enabled = prompt_cfg.get("enabled", True) if prompt_cfg else True
    max_tokens = prompt_cfg.get("max_tokens", 500) if prompt_cfg else 500

    if llm_config and enabled and llm_config.get("api_key"):
        try:
            result = await _llm_resolve(text, last_suggestion, llm_config, system_prompt, max_tokens)
            if result:
                return result
            if force_model:
                raise RuntimeError("Intent LLM returned no result (force_model=True, no heuristic fallback)")
            logger.info("Intent: LLM returned no result (client or parse failed), using heuristics")
        except Exception as e:
            if force_model:
                raise
            logger.warning("Intent LLM failed, falling back to heuristics: %s", e)

    return _heuristic_resolve(text, last_suggestion)


async def _llm_resolve(
    text: str,
    last_suggestion: Optional[str],
    llm_config: Dict[str, Any],
    system_prompt: str,
    max_tokens: int = 500,
) -> Optional[Dict[str, Any]]:
    """Call LLM to resolve intent. Returns parsed result or None on failure."""
    from packages.shared.platform_llm import get_llm_chat_client

    provider, client = get_llm_chat_client(llm_config)
    if not client:
        return None

    model = llm_config.get("model") or "gpt-4o"
    temperature = min(0.3, float(llm_config.get("temperature", 0.1)))

    user_content = f"User message: {text[:1500]}"
    if last_suggestion:
        user_content += f"\n\nLast assistant suggestion (for refinement context): {last_suggestion[:500]}"
    user_content += "\n\nReturn valid JSON only, no other text."

    try:
        if provider in ("azure", "openrouter", "custom", "openai"):
            def _call():
                return client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            response = await asyncio.to_thread(_call)
            raw = (response.choices[0].message.content or "").strip()
        elif provider == "gemini":
            gen_model = client.GenerativeModel(model)
            def _call():
                return gen_model.generate_content(
                    f"{system_prompt}\n\n{user_content}",
                    generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                )
            resp = await asyncio.to_thread(_call)
            raw = (getattr(resp, "text", None) or "").strip()
        else:
            return None

        if not raw:
            return None

        # Parse JSON (may be wrapped in markdown code block)
        if "```" in raw:
            start = raw.find("```") + 3
            if raw.startswith("```json"):
                start = 7
            end = raw.find("```", start)
            raw = raw[start:end] if end > start else raw[start:]
        parsed = json.loads(raw)

        intent_type = parsed.get("intent_type", "discover")
        if intent_type not in ("discover", "discover_composite", "checkout", "track", "support", "browse"):
            intent_type = "discover"

        out = {
            "intent_type": intent_type,
            "search_query": (parsed.get("search_query") or "").strip()[:500],
            "entities": parsed.get("entities") if isinstance(parsed.get("entities"), list) else [],
            "confidence_score": float(parsed.get("confidence_score", 0.8)),
        }
        if intent_type == "discover_composite":
            out["search_queries"] = parsed.get("search_queries") or []
            out["experience_name"] = (parsed.get("experience_name") or "experience")[:200]
        return out
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Intent LLM parse error: %s", e)
        return None


def _heuristic_resolve(text: str, last_suggestion: Optional[str] = None) -> Dict[str, Any]:
    """Heuristic fallback using action-word stripping."""
    text_lower = text.strip().lower()
    if not text_lower or text_lower in ("hi", "hello", "hey", "help"):
        return {
            "intent_type": "browse",
            "search_query": "",
            "entities": [],
            "confidence_score": 0.5,
        }

    # Checkout/track/support keywords
    if any(w in text_lower for w in ("checkout", "pay", "payment", "order")):
        return {"intent_type": "checkout", "search_query": "", "entities": [], "confidence_score": 0.7}
    if any(w in text_lower for w in ("track", "status", "where is", "shipped")):
        return {"intent_type": "track", "search_query": "", "entities": [], "confidence_score": 0.7}
    if any(w in text_lower for w in ("support", "help", "complaint", "refund")):
        return {"intent_type": "support", "search_query": "", "entities": [], "confidence_score": 0.7}

    # discover_composite: follow-up to probing (last_suggestion asked for date/budget/dietary/location)
    if last_suggestion:
        ls_lower = (last_suggestion or "").lower()
        probe_keywords = ("date night", "plan a date", "birthday party", "budget", "dietary", "preferences", "what date", "location", "occasion", "add flowers", "add something")
        if any(k in ls_lower for k in probe_keywords):
            # User is answering our probing questions
            detail_indicators = [
                "$", "dollar", "budget", "vegetarian", "vegan", "around", "dallas", "nyc", "location",
                "casual", "romantic", "adventurous",
                # Date/time answers: "any day next week", "this weekend", "friday", etc.
                "any day", "next week", "weekend", "friday", "saturday", "sunday", "tomorrow", "next month",
                "this weekend", "whenever", "flexible", "tonight", "this week",
            ]
            # User answered with specific details (date, budget, location, etc.) or short non-question
            is_answer = any(k in text_lower for k in detail_indicators) or (
                len(text_lower) <= 60
                and not any(text_lower.startswith(q) for q in ("what", "how", "can you", "could you", "i want to", "show me", "find me"))
                and "?" not in text
            )
            if is_answer:
                entities = []
                if "dallas" in text_lower or "dallas" in text:
                    entities.append({"type": "location", "value": "Dallas"})
                return {
                    "intent_type": "discover_composite",
                    "search_queries": ["flowers", "dinner", "movies"],
                    "experience_name": "date night",
                    "entities": entities,
                    "confidence_score": 0.75,
                }

    # discover_composite: heuristic detection for common experience phrases
    if "date night" in text_lower or ("plan" in text_lower and "date" in text_lower):
        return {
            "intent_type": "discover_composite",
            "search_query": "",
            "search_queries": ["flowers", "dinner", "movies"],
            "experience_name": "date night",
            "entities": [],
            "confidence_score": 0.7,
        }
    if "birthday" in text_lower and ("party" in text_lower or "celebration" in text_lower):
        return {
            "intent_type": "discover_composite",
            "search_query": "",
            "search_queries": ["cake", "flowers", "gifts"],
            "experience_name": "birthday",
            "entities": [],
            "confidence_score": 0.7,
        }
    if "picnic" in text_lower:
        return {
            "intent_type": "discover_composite",
            "search_query": "",
            "search_queries": ["basket", "blanket", "food"],
            "experience_name": "picnic",
            "entities": [],
            "confidence_score": 0.7,
        }

    # Single-category discover: use "gifts" when user asks for gifts (better catalog match)
    derived = derive_search_query(text)
    if "gift" in text_lower:
        derived = "gifts" if not derived else "gifts"

    # Extract budget: "under $50", "under 50", "within $100", "max 25"
    entities: List[Dict[str, Any]] = []
    budget_match = re.search(r"(?:under|within|max|below|less than)\s*\$?\s*(\d+)", text_lower)
    if budget_match:
        dollars = int(budget_match.group(1))
        entities.append({"type": "budget", "value": dollars * 100})  # value in cents

    return {
        "intent_type": "discover",
        "search_query": derived if derived else "browse",
        "entities": entities,
        "confidence_score": 0.6,
    }
