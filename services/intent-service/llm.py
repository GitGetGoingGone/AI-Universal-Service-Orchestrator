"""
Intent resolution: LLM when configured, heuristic fallback otherwise.
Used by intent-service API and orchestrator fallback.
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

# Probe keywords in last_suggestion indicate we asked for details
_PROBE_KEYWORDS = ("budget", "dietary", "preferences", "location", "what date", "occasion", "add flowers", "add something", "?")

# Unrelated responses when we asked probing questions
_UNRELATED_PHRASES = ("show more options", "more options", "other options", "different options", "you suggest", "suggest", "whatever", "anything")

# Composite experience patterns -> (search_queries, experience_name); proposed_plan = human-readable labels
_COMPOSITE_PATTERNS = [
    (r"date\s*night|plan\s*a\s*date|romantic\s*evening", ["flowers", "dinner", "limo"], "date night", ["Flowers", "Dinner", "Limo"]),
    (r"birthday\s*party|birthday\s*celebration", ["cake", "flowers", "gifts"], "birthday party", ["Cake", "Flowers", "Gifts"]),
    (r"picnic", ["basket", "blanket", "food"], "picnic", ["Basket", "Blanket", "Food"]),
    (r"baby\s*shower", ["cake", "decorations", "gifts"], "baby shower", ["Cake", "Decorations", "Gifts"]),
]

# Location-like short answers: do NOT use as product search_query; map to location entity only
_LOCATION_LIKE_WORDS = (
    "downtown", "midtown", "uptown", "dallas", "nyc", "brooklyn", "manhattan",
    "houston", "austin", "chicago", "la", "sf", "seattle", "boston", "miami",
    "near me", "around me", "here", "local",
)

# Budget extraction: "under $50", "$50", "50 dollars"
_BUDGET_RE = re.compile(r"(?:under|under\s+)?\$?\s*(\d+)\s*(?:dollars?|dollars?|bucks?)?", re.I)

# Refinement: "no X" / "remove X" -> category key (lowercase)
_REMOVE_PATTERNS = [
    (r"\bno\s+limo\b|remove\s+(?:the\s+)?limo|without\s+(?:the\s+)?limo|skip\s+limo", "limo"),
    (r"\bno\s+flowers\b|remove\s+(?:the\s+)?flowers|without\s+flowers|skip\s+flowers|don'?t\s+want\s+flowers", "flowers"),
    (r"\bno\s+dinner\b|remove\s+(?:the\s+)?dinner|without\s+dinner|skip\s+dinner", "dinner"),
    (r"\bno\s+chocolates\b|remove\s+(?:the\s+)?chocolates|without\s+chocolates|skip\s+chocolates", "chocolates"),
    (r"\bno\s+cake\b|remove\s+(?:the\s+)?cake|without\s+cake|skip\s+cake", "cake"),
    (r"\bno\s+movies\b|remove\s+(?:the\s+)?movies|without\s+movies|skip\s+movies", "movies"),
    (r"\bno\s+gifts\b|remove\s+(?:the\s+)?gifts|without\s+gifts", "gifts"),
    (r"\bno\s+decorations\b|remove\s+(?:the\s+)?decorations|without\s+decorations", "decorations"),
]
# Human-readable label for proposed_plan by category key
_CAT_TO_LABEL = {"limo": "Limo", "flowers": "Flowers", "dinner": "Dinner", "chocolates": "Chocolates", "cake": "Cake", "movies": "Movies", "gifts": "Gifts", "decorations": "Decorations", "basket": "Basket", "blanket": "Blanket", "food": "Food"}

# Address-like string (Identity Leak patch): digits + street-type word
_ADDRESS_RE = re.compile(r"\d+\s+\w+.*\b(st|ave|blvd|road|rd|way|ln|dr|trl|street|avenue|boulevard)\b", re.I)


def _heuristic_resolve(
    text: str,
    *,
    last_suggestion: Optional[str] = None,
    recent_conversation: Optional[List[Dict[str, Any]]] = None,
    probe_count: Optional[int] = None,
    thread_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Heuristic intent resolution when LLM is unavailable.
    Returns dict with intent_type, search_query, entities, etc.
    """
    t = (text or "").strip().lower()
    ls = (last_suggestion or "").lower()
    conv = recent_conversation or []

    # Browse: empty, hi, hello, help (when not clearly support)
    if not t or t in ("hi", "hello", "hey", "hola"):
        return {
            "intent_type": "browse",
            "search_query": "browse",
            "entities": [],
            "confidence_score": 0.9,
            "recommended_next_action": "complete_with_probing",
        }

    # Open-ended product queries: probe for experience (do not list products or call discover yet)
    _OPEN_ENDED_PRODUCT_PATTERNS = (
        r"what\s+products?\s+(do\s+you\s+)?have",
        r"what\s+do\s+you\s+have",
        r"what('s|\s+is)\s+available",
        r"show\s+me\s+(what('s|\s+you\s+have)|options|everything)",
        r"what\s+can\s+you\s+(do|offer|get)",
        r"what\s+options?\s+(do\s+you\s+)?have",
        r"what\s+(do\s+you\s+)?(sell|offer)",
        r"do\s+you\s+have\s+(any\s+)?(products?|options?)",
        r"show\s+(me\s+)?(your\s+)?(products?|stuff|things|catalog)",
        r"list\s+(all\s+)?(your\s+)?(products?|options?)",
    )
    if any(re.search(pat, t) for pat in _OPEN_ENDED_PRODUCT_PATTERNS):
        return {
            "intent_type": "browse",
            "search_query": "browse",
            "entities": [],
            "confidence_score": 0.9,
            "recommended_next_action": "complete_with_probing",
        }

    # Checkout / track / support
    if any(w in t for w in ("checkout", "pay", "payment", "order", "cart")):
        return {"intent_type": "checkout", "search_query": "", "entities": [], "confidence_score": 0.95}
    if any(w in t for w in ("track", "status", "where is", "shipped", "delivery")):
        return {"intent_type": "track", "search_query": "", "entities": [], "confidence_score": 0.95}
    if any(w in t for w in ("support", "complaint", "refund", "help me")):
        return {"intent_type": "support", "search_query": "", "entities": [], "confidence_score": 0.9}

    # Unrelated to probing: user said "show more options" etc. instead of answering
    if ls and any(k in ls for k in _PROBE_KEYWORDS):
        if any(p in t for p in _UNRELATED_PHRASES):
            sq = ["flowers", "dinner", "limo"]
            exp = "date night"
            proposed = ["Flowers", "Dinner", "Limo"]
            for c in reversed(conv):
                if isinstance(c, dict) and c.get("role") == "user":
                    msg = (c.get("content") or "").lower()
                    for pat, queries, exp_name, plan in _COMPOSITE_PATTERNS:
                        if re.search(pat, msg):
                            sq, exp, proposed = queries, exp_name, plan
                            break
                    break
            # Variety leak patch: "other options" / "something else" -> request_variety for tier rotation
            request_variety = any(
                p in t for p in ("other options", "something else", "different bundle", "another option", "show me something else")
            )
            return {
                "intent_type": "discover_composite",
                "search_query": " ".join(sq),
                "search_queries": sq,
                "experience_name": exp,
                "bundle_options": [{"label": exp, "categories": sq}],
                "entities": [],
                "proposed_plan": proposed,
                "unrelated_to_probing": True,
                "request_variety": request_variety,
                "recommended_next_action": "discover_composite",
                "confidence_score": 0.85,
            }

        # Identity leak patch: address-like string in composite context -> pickup_address/delivery_address entity, NOT search_query
        if _ADDRESS_RE.search(text or ""):
            sq = ["flowers", "dinner", "limo"]
            exp = "date night"
            proposed = ["Flowers", "Dinner", "Limo"]
            for c in reversed(conv):
                if isinstance(c, dict) and c.get("role") == "user":
                    msg = (c.get("content") or "").lower()
                    for pat, queries, exp_name, plan in _COMPOSITE_PATTERNS:
                        if re.search(pat, msg):
                            sq, exp, proposed = queries, exp_name, plan
                            break
                    break
            addr = (text or "").strip()[:200]
            return {
                "intent_type": "discover_composite",
                "search_query": " ".join(sq),
                "search_queries": sq,
                "experience_name": exp,
                "bundle_options": [{"label": exp, "categories": sq}],
                "entities": [{"type": "pickup_address", "value": addr}],
                "proposed_plan": proposed,
                "recommended_next_action": "discover_composite",
                "confidence_score": 0.9,
            }

        # Answer to composite probing: date/time, budget, or short answer (e.g. "tomorrow", "downtown")
        _DATE_TIME_WORDS = (
            "tomorrow", "today", "tonight", "this weekend", "this week", "next week", "next weekend",
            "friday", "saturday", "sunday", "monday", "tuesday", "wednesday", "thursday",
            "anytime", "whenever", "flexible",
        )
        is_date_answer = any(w in t for w in _DATE_TIME_WORDS) or re.search(r"\b\d{1,2}/\d{1,2}\b", t)
        budget_match = _BUDGET_RE.search(text)
        is_budget_answer = budget_match is not None
        is_short_answer = len(t.split()) <= 4 and not re.search(r"actually|forget|want\s+chocolates|want\s+flowers", t)

        if is_date_answer or is_budget_answer or is_short_answer:
            sq = ["flowers", "dinner", "limo"]
            exp = "date night"
            proposed = ["Flowers", "Dinner", "Limo"]
            for c in reversed(conv):
                if isinstance(c, dict) and c.get("role") == "user":
                    msg = (c.get("content") or "").lower()
                    for pat, queries, exp_name, plan in _COMPOSITE_PATTERNS:
                        if re.search(pat, msg):
                            sq, exp, proposed = queries, exp_name, plan
                            break
                    break
            entities: List[Dict[str, Any]] = []
            if is_date_answer:
                entities.append({"type": "time", "value": text.strip()[:100]})
            if is_budget_answer and budget_match:
                entities.append({"type": "budget", "value": int(budget_match.group(1)) * 100})
            if is_short_answer and not is_date_answer and not is_budget_answer and len(t) > 1:
                if not any(w in t for w in ("no", "any", "whatever", "surprise", "you choose")):
                    entities.append({"type": "location", "value": text.strip()[:100]})

            return {
                "intent_type": "discover_composite",
                "search_query": " ".join(sq),
                "search_queries": sq,
                "experience_name": exp,
                "bundle_options": [{"label": exp, "categories": sq}],
                "entities": entities,
                "proposed_plan": proposed,
                "recommended_next_action": "discover_composite",
                "confidence_score": 0.9,
            }

    # Fallback: date/time (e.g. "today") without last_suggestion — if conversation has composite request, treat as answer
    _DATE_TIME_WORDS = (
        "tomorrow", "today", "tonight", "this weekend", "this week", "next week", "next weekend",
        "friday", "saturday", "sunday", "monday", "tuesday", "wednesday", "thursday",
        "anytime", "whenever", "flexible",
    )
    if any(w in t for w in _DATE_TIME_WORDS) or re.search(r"\b\d{1,2}/\d{1,2}\b", t):
        for c in reversed(conv):
            if isinstance(c, dict) and c.get("role") == "user":
                msg = (c.get("content") or "").lower()
                if msg == t:
                    continue
                for pat, queries, exp_name, plan in _COMPOSITE_PATTERNS:
                    if re.search(pat, msg):
                        return {
                            "intent_type": "discover_composite",
                            "search_query": " ".join(queries),
                            "search_queries": list(queries),
                            "experience_name": exp_name,
                            "bundle_options": [{"label": exp_name, "categories": list(queries)}],
                            "entities": [{"type": "time", "value": text.strip()[:100]}],
                            "proposed_plan": list(plan),
                            "recommended_next_action": "discover_composite",
                            "confidence_score": 0.85,
                        }
                break

    # "More options" / "other options" after we showed a composite bundle — re-fetch bundle, don't product-search
    _MORE_OPTIONS_PHRASES = (
        "more options", "other options", "different options", "any other", "do you have more",
        "show more", "got anything else", "anything else", "other choices", "alternatives",
    )
    if any(p in t for p in _MORE_OPTIONS_PHRASES):
        # "More options" after a simple product list (discover): reuse previous search query so we don't ask for date/area
        from packages.shared.discovery import derive_search_query
        prev_user_msgs = [c.get("content", "") or "" for c in conv if isinstance(c, dict) and c.get("role") == "user"]
        for prev_msg in reversed(prev_user_msgs):
            prev_msg = (prev_msg or "").strip()
            if not prev_msg or prev_msg.lower() == t.lower():
                continue
            prev_query = derive_search_query(prev_msg)
            if prev_query and prev_query not in ("more", "options", "browse"):
                # User was in simple discover (e.g. "baby products", "looking for baby products"); give more of same
                return {
                    "intent_type": "discover",
                    "search_query": prev_query,
                    "entities": [],
                    "recommended_next_action": "discover_products",
                    "confidence_score": 0.85,
                }

        # Composite context: last suggestion or assistant message has composite framing (not just "bundle" in product names)
        in_composite_context = False
        _composite_signals = ("date night", "total:", "add this bundle", "add this", "curated", "option 1 of", "plan a perfect")
        if ls and any(s in ls.lower() for s in _composite_signals):
            in_composite_context = True
        for c in conv:
            if isinstance(c, dict) and c.get("role") == "assistant" and (c.get("content") or ""):
                msg = (c.get("content") or "").lower()
                if any(s in msg for s in _composite_signals):
                    in_composite_context = True
                    break
        if not in_composite_context:
            for c in conv:
                if isinstance(c, dict) and c.get("role") == "user" and (c.get("content") or ""):
                    ucontent = (c.get("content") or "").lower()
                    if "not " in ucontent and "shower" in ucontent:
                        continue  # "not baby shower" -> user wants products, not composite
                    if "looking for" in ucontent and "product" in ucontent:
                        continue  # "looking for baby products" -> simple discover
                    for pat, _, _ in _COMPOSITE_PATTERNS:
                        if re.search(pat, ucontent):
                            in_composite_context = True
                            break
                    break
        if in_composite_context:
            sq = ["flowers", "dinner", "limo"]
            exp = "date night"
            proposed = ["Flowers", "Dinner", "Limo"]
            for c in reversed(conv):
                if isinstance(c, dict) and c.get("role") == "user":
                    msg = (c.get("content") or "").lower()
                    for pat, queries, exp_name, plan in _COMPOSITE_PATTERNS:
                        if re.search(pat, msg):
                            sq, exp, proposed = queries, exp_name, plan
                            break
                    break
            return {
                "intent_type": "discover_composite",
                "search_query": " ".join(sq),
                "search_queries": sq,
                "experience_name": exp,
                "bundle_options": [{"label": exp, "categories": sq}],
                "entities": [],
                "proposed_plan": proposed,
                "unrelated_to_probing": True,
                "recommended_next_action": "discover_composite",
                "confidence_score": 0.85,
            }

    # Refinement leak patch: "no limo", "remove the flowers", "skip chocolates" -> refine_composite + removed_categories
    removed: List[str] = []
    for pat, cat in _REMOVE_PATTERNS:
        if re.search(pat, t):
            removed.append(cat)
    if removed:
        sq = ["flowers", "dinner", "limo"]
        exp = "date night"
        proposed = ["Flowers", "Dinner", "Limo"]
        for c in reversed(conv):
            if isinstance(c, dict) and c.get("role") == "user":
                msg = (c.get("content") or "").lower()
                for pattern, queries, exp_name, plan in _COMPOSITE_PATTERNS:
                    if re.search(pattern, msg):
                        sq, exp, proposed = list(queries), exp_name, list(plan)
                        break
                break
        removed_set = set(removed)
        sq_purged = [q for q in sq if q.lower() not in removed_set]
        label_to_key = {v.lower(): k for k, v in _CAT_TO_LABEL.items()}
        proposed_purged = [lbl for lbl in proposed if label_to_key.get(lbl.lower(), lbl.lower()) not in removed_set]
        if not proposed_purged and sq_purged:
            proposed_purged = [_CAT_TO_LABEL.get(q, q.capitalize()) for q in sq_purged]
        return {
            "intent_type": "refine_composite",
            "search_query": " ".join(sq_purged),
            "search_queries": sq_purged,
            "experience_name": exp,
            "bundle_options": [{"label": exp, "categories": sq_purged}],
            "removed_categories": list(removed),
            "entities": [],
            "proposed_plan": proposed_purged,
            "recommended_next_action": "discover_composite",
            "confidence_score": 0.9,
        }

    # Location-only short answer in composite context: do NOT create product search for "downtown"
    words = t.split()
    if len(words) <= 3 and any(w in t for w in _LOCATION_LIKE_WORDS):
        for c in reversed(conv):
            if isinstance(c, dict) and c.get("role") == "user":
                msg = (c.get("content") or "").lower()
                for pat, queries, exp_name, plan in _COMPOSITE_PATTERNS:
                    if re.search(pat, msg):
                        return {
                            "intent_type": "discover_composite",
                            "search_query": " ".join(queries),
                            "search_queries": list(queries),
                            "experience_name": exp_name,
                            "bundle_options": [{"label": exp_name, "categories": list(queries)}],
                            "entities": [{"type": "location", "value": text.strip()[:100]}],
                            "proposed_plan": list(plan),
                            "recommended_next_action": "discover_composite",
                            "confidence_score": 0.88,
                        }
                break

    # Topic change: "actually I want X", "forget that, X"
    if re.search(r"actually\s+i\s+want|forget\s+that|never\s+mind", t):
        from packages.shared.discovery import derive_search_query
        derived = derive_search_query(text)
        return {
            "intent_type": "discover",
            "search_query": derived or text.strip()[:50] or "browse",
            "entities": [],
            "confidence_score": 0.9,
            "recommended_next_action": "discover_products",
        }

    # Composite: date night, picnic, birthday party, etc.
    for pat, queries, exp_name, plan in _COMPOSITE_PATTERNS:
        if re.search(pat, t):
            return {
                "intent_type": "discover_composite",
                "search_query": " ".join(queries),
                "search_queries": queries,
                "experience_name": exp_name,
                "bundle_options": [{"label": exp_name, "categories": queries}],
                "entities": [],
                "proposed_plan": list(plan),
                "recommended_next_action": "complete_with_probing",
                "confidence_score": 0.9,
            }

    # Gift without recipient: probe
    if "gift" in t or "birthday" in t:
        from packages.shared.discovery import derive_search_query
        derived = derive_search_query(text)
        entities = []
        budget_match = _BUDGET_RE.search(text)
        if budget_match:
            cents = int(budget_match.group(1)) * 100
            entities.append({"type": "budget", "value": cents})
        return {
            "intent_type": "discover",
            "search_query": derived or "gifts",
            "entities": entities,
            "recommended_next_action": "complete_with_probing" if not entities else "discover_products",
            "confidence_score": 0.85,
        }

    # Default: discover
    from packages.shared.discovery import derive_search_query
    derived = derive_search_query(text)
    entities = []
    budget_match = _BUDGET_RE.search(text)
    if budget_match:
        entities.append({"type": "budget", "value": int(budget_match.group(1)) * 100})
    return {
        "intent_type": "discover",
        "search_query": derived or (text.strip()[:50] if text else "browse"),
        "entities": entities,
        "recommended_next_action": "discover_products" if derived else "complete_with_probing",
        "confidence_score": 0.8,
    }


async def resolve_intent(
    text: str,
    *,
    user_id: Optional[str] = None,
    last_suggestion: Optional[str] = None,
    recent_conversation: Optional[List[Dict[str, Any]]] = None,
    probe_count: Optional[int] = None,
    thread_context: Optional[Dict[str, Any]] = None,
    experience_categories: Optional[List[str]] = None,
    force_model: bool = False,
) -> Dict[str, Any]:
    """
    Resolve intent from natural language.
    Uses LLM when configured (platform_config + llm_providers); falls back to heuristics.
    When force_model=True, LLM only; no heuristic fallback on failure.
    """
    from db import get_supabase
    from packages.shared.platform_llm import get_platform_llm_config, get_llm_chat_client
    from packages.shared.platform_llm import get_model_interaction_prompt
    from packages.shared.prompts import get_intent_system_prompt

    client = get_supabase()
    llm_config = get_platform_llm_config(client) if client else None

    if not llm_config or not llm_config.get("api_key"):
        return _heuristic_resolve(
            text,
            last_suggestion=last_suggestion,
            recent_conversation=recent_conversation,
            probe_count=probe_count,
            thread_context=thread_context,
        )

    # Refinement short-circuit: "no limo" / "remove flowers" etc. in composite context -> use heuristic so we get refine_composite
    t = (text or "").strip().lower()
    for pat, _ in _REMOVE_PATTERNS:
        if re.search(pat, t):
            ls = (last_suggestion or "").lower()
            conv = list(recent_conversation or [])
            in_composite = bool(
                "date night" in ls or ("flowers" in ls and "dinner" in ls) or "limo" in ls
                or "flowers and dinner" in ls or "proposed_plan" in ls
            )
            if not in_composite and conv:
                for c in reversed(conv):
                    if isinstance(c, dict) and (c.get("role") or "").lower() == "assistant":
                        ac = (c.get("content") or "").lower()
                        if "date night" in ac or ("flowers" in ac and "dinner" in ac) or "limo" in ac:
                            in_composite = True
                        break
            if in_composite:
                return _heuristic_resolve(
                    text,
                    last_suggestion=last_suggestion,
                    recent_conversation=recent_conversation,
                    probe_count=probe_count,
                    thread_context=thread_context,
                )
            break

    prompt_cfg = get_model_interaction_prompt(client, "intent") if client else None
    system_prompt = (prompt_cfg.get("system_prompt") if prompt_cfg else None) or get_intent_system_prompt()
    if not system_prompt:
        system_prompt = "You are an intent classifier. Return JSON: intent_type, search_query, search_queries, experience_name, bundle_options, entities, recommended_next_action, proposed_plan, confidence_score."

    provider, chat_client = get_llm_chat_client(llm_config)
    if not chat_client:
        if force_model:
            raise RuntimeError("LLM configured but client creation failed")
        return _heuristic_resolve(text, last_suggestion=last_suggestion, recent_conversation=recent_conversation, probe_count=probe_count, thread_context=thread_context)

    model = llm_config.get("model") or "gpt-4o"
    temperature = float(llm_config.get("temperature", 0.1))
    max_tokens = prompt_cfg.get("max_tokens", 500) if prompt_cfg else 500

    user_content = f"User message: {text}"
    if last_suggestion:
        user_content += f"\nLast suggestion: {last_suggestion[:300]}"
    if recent_conversation:
        conv_str = "; ".join(f"{c.get('role','')}: {(c.get('content') or '')[:80]}" for c in recent_conversation[-4:] if isinstance(c, dict))
        user_content += f"\nRecent conversation: {conv_str}"
    if experience_categories:
        user_content += f"\nAvailable experience categories (use for theme bundle options experience_tags): {', '.join(str(t) for t in experience_categories)}"
    user_content += "\n\nReturn valid JSON only. For discover_composite, include bundle_options with label, description, categories, and optionally experience_tags (e.g. [\"romantic\"]) per option. For multi-tag intents (e.g. 'luxury travel-friendly night out') you may set theme_experience_tags to an array of tags (AND filter; e.g. [\"luxury\", \"travel-friendly\"]); otherwise use theme_experience_tag (single string)."

    try:
        if provider in ("azure", "openrouter", "custom", "openai"):
            def _call():
                return chat_client.chat.completions.create(
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
            gen_model = chat_client.GenerativeModel(model)
            def _call():
                return gen_model.generate_content(
                    f"{system_prompt}\n\n{user_content}",
                    generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
                )
            resp = await asyncio.to_thread(_call)
            raw = (getattr(resp, "text", None) or "").strip()
        else:
            if force_model:
                raise RuntimeError("Unsupported LLM provider")
            return _heuristic_resolve(text, last_suggestion=last_suggestion, recent_conversation=recent_conversation, probe_count=probe_count, thread_context=thread_context)

        # Parse JSON from response (may be wrapped in markdown)
        if "```" in raw:
            raw = re.sub(r"```(?:json)?\s*", "", raw)
            raw = raw.split("```")[0].strip()
        parsed = json.loads(raw)
        if not isinstance(parsed, dict) or not parsed.get("intent_type"):
            raise ValueError("Invalid parsed intent")
        return parsed
    except Exception:
        if force_model:
            raise
        return _heuristic_resolve(
            text,
            last_suggestion=last_suggestion,
            recent_conversation=recent_conversation,
            probe_count=probe_count,
            thread_context=thread_context,
        )
