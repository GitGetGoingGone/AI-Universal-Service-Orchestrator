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
    recent_conversation: Optional[List[Dict[str, Any]]] = None,
    probe_count: Optional[int] = None,
    thread_context: Optional[Dict[str, Any]] = None,
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
            'You are an intent classifier. Return JSON: {"intent_type":"discover|discover_composite|checkout|track|support|browse","search_query":"","search_queries":[],"experience_name":"","entities":[],"confidence_score":0.7}. '
            "Use discover_composite for composed experiences (date night, birthday, picnic, anniversary, brunch, etc.)."
        )
    enabled = prompt_cfg.get("enabled", True) if prompt_cfg else True
    max_tokens = prompt_cfg.get("max_tokens", 500) if prompt_cfg else 500

    if llm_config and enabled and llm_config.get("api_key"):
        try:
            result = await _llm_resolve(
                text, last_suggestion, llm_config, system_prompt, max_tokens,
                recent_conversation=recent_conversation,
                probe_count=probe_count,
                thread_context=thread_context,
            )
            if result:
                return result
            if force_model:
                raise RuntimeError("Intent LLM returned no result (force_model=True, no heuristic fallback)")
            logger.info("Intent: LLM returned no result (client or parse failed), using heuristics")
        except Exception as e:
            if force_model:
                raise
            logger.warning("Intent LLM failed, falling back to heuristics: %s", e)

    return _heuristic_resolve(
        text, last_suggestion,
        recent_conversation=recent_conversation,
        probe_count=probe_count,
        thread_context=thread_context,
    )


async def _llm_resolve(
    text: str,
    last_suggestion: Optional[str],
    llm_config: Dict[str, Any],
    system_prompt: str,
    max_tokens: int = 500,
    *,
    recent_conversation: Optional[List[Dict[str, Any]]] = None,
    probe_count: Optional[int] = None,
    thread_context: Optional[Dict[str, Any]] = None,
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
    if recent_conversation:
        conv_str = "\n".join(
            f"{m.get('role', '')}: {(m.get('content') or '')[:80]}" for m in recent_conversation[-4:]
        )
        if conv_str:
            user_content += f"\n\nRecent conversation:\n{conv_str[:400]}"
    if probe_count is not None and probe_count > 0:
        user_content += f"\n\nProbe count: {probe_count}"
    if thread_context:
        parts = []
        if thread_context.get("order_id"):
            parts.append("order_id")
        if thread_context.get("bundle_id"):
            parts.append("bundle_id")
        if parts:
            user_content += f"\n\nThread context: {', '.join(parts)}"
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
        if intent_type not in ("discover", "discover_composite", "refine_composite", "checkout", "track", "support", "browse"):
            intent_type = "discover"

        out = {
            "intent_type": intent_type,
            "search_query": (parsed.get("search_query") or "").strip()[:500],
            "entities": parsed.get("entities") if isinstance(parsed.get("entities"), list) else [],
            "confidence_score": float(parsed.get("confidence_score", 0.8)),
        }
        if intent_type == "refine_composite":
            out["category_to_change"] = (parsed.get("category_to_change") or "").strip()[:100]
            out["recommended_next_action"] = "refine_bundle_category"
        elif intent_type == "discover_composite":
            out["experience_name"] = (parsed.get("experience_name") or "experience")[:200]
            bundle_opts = parsed.get("bundle_options")
            if isinstance(bundle_opts, list) and bundle_opts:
                out["bundle_options"] = [
                    {"label": str(o.get("label", "Option")), "description": str(o.get("description", "")), "categories": [str(c) for c in (o.get("categories") or []) if c]}
                    for o in bundle_opts[:10] if isinstance(o, dict)
                ]
            else:
                # Fallback: derive from search_queries (legacy)
                sq = parsed.get("search_queries") or []
                if sq:
                    out["bundle_options"] = [{"label": "Bundle", "description": "", "categories": [str(c) for c in sq if c]}]
                else:
                    out["bundle_options"] = []
            out["search_queries"] = _bundle_options_to_search_queries(out.get("bundle_options", []))
            if parsed.get("unrelated_to_probing"):
                out["unrelated_to_probing"] = True
        rec = parsed.get("recommended_next_action")
        if rec and str(rec) in ("discover_composite", "discover_products", "refine_bundle_category", "complete_with_probing", "handle_unrelated", "complete"):
            out["recommended_next_action"] = str(rec)
        return out
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Intent LLM parse error: %s", e)
        return None


def _bundle_options_to_search_queries(bundle_options: List[Dict[str, Any]]) -> List[str]:
    """Extract unique categories from bundle_options for discovery (fetch products for all)."""
    seen: set = set()
    out: List[str] = []
    for o in bundle_options:
        if isinstance(o, dict):
            for c in (o.get("categories") or []):
                s = str(c).strip()
                if s and s not in seen:
                    seen.add(s)
                    out.append(s)
    return out


def _extract_experience_name(text: str) -> Optional[str]:
    """Extract experience name from probing/context text using common patterns."""
    if not text or not isinstance(text, str):
        return None
    lower = text.strip().lower()
    # Patterns: "plan a date night", "for your birthday party", "for a picnic", "anniversary dinner"
    patterns = [
        r"plan\s+(?:a|an|the)\s+([a-z]+(?:\s+[a-z]+){0,2})",
        r"for\s+your\s+([a-z]+(?:\s+[a-z]+){0,2})",
        r"for\s+(?:a|an)\s+([a-z]+(?:\s+[a-z]+)?)",
        r"([a-z]+)\s+party",
        r"([a-z]+)\s+celebration",
        r"([a-z]+)\s+experience",
    ]
    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            name = m.group(1).strip()
            if len(name) > 2 and name not in ("the", "a", "an", "your", "our"):
                return name.replace(" ", "_") if " " in name else name
    return None


def _derive_composite_categories(text: str) -> List[str]:
    """Derive product categories from text when LLM is not available. No hardcoded experiences."""
    derived = derive_search_query(text or "")
    if derived and derived.strip() and derived.lower() not in ("browse", "show", "options"):
        # If derived is a long sentence (assistant probing message), it's not a product query
        if len(derived) > 50:
            return []
        return [derived.strip()]
    return ["gifts"]


def _experience_name_to_default_categories(exp: Optional[str]) -> List[str]:
    """Map experience name to default product categories for discovery. Used when probing follow-up."""
    if not exp:
        return ["flowers", "dinner", "gifts"]
    lower = exp.lower().replace("_", " ")
    if "date" in lower and "night" in lower:
        return ["flowers", "dinner", "limo"]
    if "date" in lower:
        return ["flowers", "dinner", "gifts"]
    if "birthday" in lower or "party" in lower:
        return ["cake", "party", "gifts"]
    if "picnic" in lower:
        return ["picnic", "food", "beverages"]
    if "anniversary" in lower:
        return ["flowers", "dinner", "gifts"]
    if "brunch" in lower:
        return ["brunch", "food", "beverages"]
    if "dinner" in lower:
        return ["dinner", "flowers", "dessert"]
    return ["flowers", "dinner", "gifts"]


def _experience_from_probing(
    last_suggestion_lower: str,
    recent_conversation: Optional[List[Dict[str, Any]]] = None,
) -> tuple:
    """Derive bundle_options and experience_name from probing context. Use USER message for categories, not assistant's probing text."""
    exp = _extract_experience_name(last_suggestion_lower)
    # Derive categories from the most recent USER message (e.g. "plan a date night"), not from assistant's probing
    user_text = ""
    categories: List[str] = []
    if recent_conversation:
        for m in reversed(recent_conversation):
            if isinstance(m, dict) and (m.get("role") or "").lower() == "user":
                user_text = (m.get("content") or m.get("text") or "")[:500]
                break
            if isinstance(m, str) and "user:" in m.lower():
                user_text = m.split(":", 1)[-1].strip()[:500]
                break
    if user_text:
        categories = _derive_composite_categories(user_text)
        # If derived looks like experience phrase (e.g. "plan date night") not product terms, use defaults
        exp_phrases = ("plan", "date", "night", "party", "picnic", "anniversary", "brunch", "celebration")
        if categories and any(p in (categories[0] or "").lower() for p in exp_phrases):
            categories = _experience_name_to_default_categories(exp)
    if not categories:
        categories = _experience_name_to_default_categories(exp)
    opts = [{"label": (exp or "Bundle").replace("_", " ").title(), "description": "", "categories": categories}]
    return (opts, exp or "experience")


def _heuristic_resolve(
    text: str,
    last_suggestion: Optional[str] = None,
    *,
    recent_conversation: Optional[List[Dict[str, Any]]] = None,
    probe_count: Optional[int] = None,
    thread_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Heuristic fallback using action-word stripping."""
    text_lower = text.strip().lower()
    if not text_lower or text_lower in ("hi", "hello", "hey", "help"):
        return {
            "intent_type": "browse",
            "search_query": "",
            "entities": [],
            "confidence_score": 0.5,
            "recommended_next_action": "complete_with_probing",
        }

    # refine_composite: change category in bundle (requires bundle_id in thread_context)
    if thread_context and thread_context.get("bundle_id"):
        change_phrases = ("change the ", "change my ", "different ", "swap the ", "swap my ", "replace the ", "other ", "another ", "i want different ", "switch the ")
        if any(p in text_lower for p in change_phrases):
            cat = derive_search_query(text)
            if cat and cat.strip():
                return {
                    "intent_type": "refine_composite",
                    "category_to_change": cat.strip(),
                    "entities": [],
                    "confidence_score": 0.8,
                    "recommended_next_action": "refine_bundle_category",
                }

    # Checkout/track/support keywords
    if any(w in text_lower for w in ("checkout", "pay", "payment", "order")):
        return {"intent_type": "checkout", "search_query": "", "entities": [], "confidence_score": 0.7, "recommended_next_action": "complete"}
    if any(w in text_lower for w in ("track", "status", "where is", "shipped")):
        return {"intent_type": "track", "search_query": "", "entities": [], "confidence_score": 0.7, "recommended_next_action": "complete"}
    if any(w in text_lower for w in ("support", "help", "complaint", "refund")):
        return {"intent_type": "support", "search_query": "", "entities": [], "confidence_score": 0.7, "recommended_next_action": "complete"}

    # discover_composite: follow-up to probing (last_suggestion asked for date/budget/dietary/location)
    if last_suggestion:
        ls_lower = (last_suggestion or "").lower()
        probe_keywords = ("plan a ", "plan an ", "party", "budget", "dietary", "preferences", "what date", "location", "occasion", "add flowers", "add something")
        if any(k in ls_lower for k in probe_keywords):
            # User is answering our probing questions (date, budget, location, etc.)
            detail_indicators = [
                "$", "dollar", "budget", "vegetarian", "vegan", "around", "dallas", "nyc", "location",
                "casual", "romantic", "adventurous",
                # Date/time answers: "any day next week", "this weekend", "friday", etc.
                "any day", "next week", "weekend", "friday", "saturday", "sunday", "tomorrow", "next month",
                "this weekend", "whenever", "flexible", "tonight", "this week", "anytime",
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
                opts, exp = _experience_from_probing(ls_lower, recent_conversation)
                return {
                    "intent_type": "discover_composite",
                    "bundle_options": opts,
                    "search_queries": _bundle_options_to_search_queries(opts),
                    "experience_name": exp,
                    "entities": entities,
                    "confidence_score": 0.75,
                    "recommended_next_action": "discover_composite",
                }
            # User did not answer probing but wants to see options ("show more options", "more options", etc.)
            fetch_more_phrases = ("show me more", "more options", "other options", "just show me", "show me something", "show options", "show me options")
            if any(p in text_lower for p in fetch_more_phrases):
                opts, exp = _experience_from_probing(ls_lower, recent_conversation)
                return {
                    "intent_type": "discover_composite",
                    "bundle_options": opts,
                    "search_queries": _bundle_options_to_search_queries(opts),
                    "experience_name": exp,
                    "entities": [],
                    "confidence_score": 0.8,
                    "recommended_next_action": "discover_composite",
                }
            # Other unrelated responses (e.g. "what's the weather") → probe gracefully
            opts, exp = _experience_from_probing(ls_lower, recent_conversation)
            return {
                "intent_type": "discover_composite",
                "bundle_options": opts,
                "search_queries": _bundle_options_to_search_queries(opts),
                "experience_name": exp,
                "entities": [],
                "unrelated_to_probing": True,
                "confidence_score": 0.7,
                "recommended_next_action": "handle_unrelated",
            }

    # discover_composite: heuristic detection for composite experience phrases
    # "plan a X", "X party", "X celebration", "for a X" - supports many experience types
    composite_indicators = (
        "plan a ", "plan an ", "plan the ",
        " party", " celebration", " experience",
        "plan ", "organize ", "put together ",
    )
    composite_match = any(ind in text_lower for ind in composite_indicators) or re.search(
        r"\b(plan|organize|arrange)\b.*\b(date|birthday|picnic|anniversary|brunch|dinner|outing)\b", text_lower
    )
    if composite_match or "gift bundle" in text_lower or "create gift bundle" in text_lower:
        exp = _extract_experience_name(text_lower) or "experience"
        categories = _derive_composite_categories(text_lower)
        opts = [{"label": (exp or "Bundle").replace("_", " ").title(), "description": "", "categories": categories}]
        return {
            "intent_type": "discover_composite",
            "search_query": "",
            "bundle_options": opts,
            "search_queries": _bundle_options_to_search_queries(opts),
            "experience_name": exp,
            "entities": [],
            "confidence_score": 0.7,
            "recommended_next_action": "complete_with_probing",
        }

    # Single-category discover: use "gifts" when user asks for gifts (better catalog match)
    derived = derive_search_query(text)
    if "gift" in text_lower:
        derived = "gifts" if not derived else "gifts"

    # Generic queries: engage first before discover_products
    generic_queries = ("browse", "show", "options", "what", "looking", "stuff", "things", "got", "have", "products", "all")
    generic_phrases = (
        "show me", "what do you have", "what have you", "what's available", "what can you", "show me what",
        "what all products", "what products", "products do you have", "what have you got", "what do you offer",
        "what do you sell", "what are my options", "what can i get", "what do you got",
    )
    sq = (derived or "browse").lower().strip()
    is_generic = not sq or sq in generic_queries or any(g in text_lower for g in generic_phrases)
    if is_generic:
        rec = "complete_with_probing"
        sq = "browse"  # Use browse for generic catalog queries
    else:
        rec = "discover_products"

    # Extract budget: "under $50", "under 50", "within $100", "max 25"
    entities: List[Dict[str, Any]] = []
    budget_match = re.search(r"(?:under|within|max|below|less than)\s*\$?\s*(\d+)", text_lower)
    if budget_match:
        dollars = int(budget_match.group(1))
        entities.append({"type": "budget", "value": dollars * 100})  # value in cents

    return {
        "intent_type": "discover",
        "search_query": sq,
        "entities": entities,
        "confidence_score": 0.6,
        "recommended_next_action": rec,
    }
