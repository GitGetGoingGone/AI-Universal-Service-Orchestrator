"""
Intent resolution: LLM when configured, heuristic fallback otherwise.
Used by intent-service API and orchestrator fallback.
Heuristic keywords and patterns are loaded from platform_config.intent_heuristic_config (admin UI).
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional, Tuple

# Budget extraction: "under $50", "$50", "50 dollars"
_BUDGET_RE = re.compile(r"(?:under|under\s+)?\$?\s*(\d+)\s*(?:dollars?|dollars?|bucks?)?", re.I)

# Address-like string (Identity Leak patch): digits + street-type word
_ADDRESS_RE = re.compile(r"\d+\s+\w+.*\b(st|ave|blvd|road|rd|way|ln|dr|trl|street|avenue|boulevard)\b", re.I)


def _default_intent_heuristic_config() -> Dict[str, Any]:
    """Built-in defaults when platform_config.intent_heuristic_config is missing. Admin should override via Platform Config > Discovery > Intent heuristics."""
    return {
        "probe_keywords": ("budget", "dietary", "preferences", "location", "what date", "occasion", "add flowers", "add something", "?"),
        "unrelated_phrases": ("show more options", "more options", "other options", "different options", "you suggest", "suggest", "whatever", "anything"),
        "open_ended_product_patterns": (
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
        ),
        "date_time_words": (
            "tomorrow", "today", "tonight", "this weekend", "this week", "next week", "next weekend",
            "friday", "saturday", "sunday", "monday", "tuesday", "wednesday", "thursday",
            "anytime", "whenever", "flexible",
        ),
        "more_options_phrases": (
            "more options", "other options", "different options", "any other", "do you have more",
            "show more", "got anything else", "anything else", "other choices", "alternatives",
        ),
        "composite_signals": (
            "date night", "total:", "add this bundle", "add this", "curated", "option 1 of", "plan a perfect",
        ),
        "short_answer_exclude_words": ("no", "any", "whatever", "surprise", "you choose"),
        "composite_patterns": [
            (r"date\s*night|plan\s*a\s*date|romantic\s*evening", ["flowers", "dinner", "limo"], "date night", ["Flowers", "Dinner", "Limo"]),
            (r"birthday\s*party|birthday\s*celebration", ["cake", "flowers", "gifts"], "birthday party", ["Cake", "Flowers", "Gifts"]),
            (r"picnic", ["basket", "blanket", "food"], "picnic", ["Basket", "Blanket", "Food"]),
            (r"baby\s*shower", ["cake", "decorations", "gifts"], "baby shower", ["Cake", "Decorations", "Gifts"]),
        ],
        "simple_discover_keywords": ("gift", "gifts"),
        "discover_with_probe_keywords": ("gift", "birthday"),
        "location_like_words": (
            "downtown", "midtown", "uptown", "dallas", "nyc", "brooklyn", "manhattan",
            "houston", "austin", "chicago", "la", "sf", "seattle", "boston", "miami",
            "near me", "around me", "here", "local",
        ),
        "remove_patterns": [
            (r"\bno\s+limo\b|remove\s+(?:the\s+)?limo|without\s+(?:the\s+)?limo|skip\s+limo", "limo"),
            (r"\bno\s+flowers\b|remove\s+(?:the\s+)?flowers|without\s+flowers|skip\s+flowers|don'?t\s+want\s+flowers", "flowers"),
            (r"\bno\s+dinner\b|remove\s+(?:the\s+)?dinner|without\s+dinner|skip\s+dinner", "dinner"),
            (r"\bno\s+chocolates\b|remove\s+(?:the\s+)?chocolates|without\s+chocolates|skip\s+chocolates", "chocolates"),
            (r"\bno\s+cake\b|remove\s+(?:the\s+)?cake|without\s+cake|skip\s+cake", "cake"),
            (r"\bno\s+movies\b|remove\s+(?:the\s+)?movies|without\s+movies|skip\s+movies", "movies"),
            (r"\bno\s+gifts\b|remove\s+(?:the\s+)?gifts|without\s+gifts", "gifts"),
            (r"\bno\s+decorations\b|remove\s+(?:the\s+)?decorations|without\s+decorations", "decorations"),
        ],
        "cat_to_label": {"limo": "Limo", "flowers": "Flowers", "dinner": "Dinner", "chocolates": "Chocolates", "cake": "Cake", "movies": "Movies", "gifts": "Gifts", "decorations": "Decorations", "basket": "Basket", "blanket": "Blanket", "food": "Food"},
    }


def _first_composite(cfg: Dict[str, Any]) -> Tuple[List[str], str, List[str]]:
    """Default (sq, experience_name, proposed_plan) from first composite pattern when conversation doesn't match."""
    patterns = cfg.get("composite_patterns") or []
    if patterns:
        _, sq, exp, plan = patterns[0]
        return (list(sq), str(exp), list(plan))
    return (["flowers", "dinner", "limo"], "date night", ["Flowers", "Dinner", "Limo"])


def get_intent_heuristic_config() -> Dict[str, Any]:
    """
    Load intent heuristic config from platform_config.intent_heuristic_config.
    Returns normalized dict with tuple/list values for use in _heuristic_resolve.
    Falls back to _default_intent_heuristic_config() when DB is unavailable or config empty.
    """
    try:
        from db import get_supabase
        client = get_supabase()
        if not client:
            return _default_intent_heuristic_config()
        r = client.table("platform_config").select("intent_heuristic_config").limit(1).execute()
        raw = (r.data[0] if r.data else {}).get("intent_heuristic_config") if r.data else None
        if not raw or not isinstance(raw, dict):
            return _default_intent_heuristic_config()
    except Exception:
        return _default_intent_heuristic_config()

    def _str_list(val: Any, default: Tuple[str, ...]) -> Tuple[str, ...]:
        if isinstance(val, list):
            return tuple(str(x).strip() for x in val if x)
        return default

    def _composite_patterns(val: Any, default: List[Tuple[str, List[str], str, List[str]]]) -> List[Tuple[str, List[str], str, List[str]]]:
        if not isinstance(val, list):
            return default
        out: List[Tuple[str, List[str], str, List[str]]] = []
        for item in val:
            if not isinstance(item, dict):
                continue
            pat = item.get("pattern")
            q = item.get("search_queries")
            name = item.get("experience_name")
            plan = item.get("proposed_plan")
            if pat and isinstance(q, list) and name is not None and isinstance(plan, list):
                out.append((str(pat), list(q), str(name), list(plan)))
        return out if out else default

    def _remove_patterns(val: Any, default: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        if not isinstance(val, list):
            return default
        out: List[Tuple[str, str]] = []
        for item in val:
            if isinstance(item, dict) and item.get("pattern") and item.get("category_key"):
                out.append((str(item["pattern"]), str(item["category_key"])))
        return out if out else default

    def _cat_to_label(val: Any, default: Dict[str, str]) -> Dict[str, str]:
        if isinstance(val, dict):
            return {str(k): str(v) for k, v in val.items() if k and v}
        return default

    defaults = _default_intent_heuristic_config()
    return {
        "probe_keywords": _str_list(raw.get("probe_keywords"), defaults["probe_keywords"]),
        "unrelated_phrases": _str_list(raw.get("unrelated_phrases"), defaults["unrelated_phrases"]),
        "open_ended_product_patterns": _str_list(raw.get("open_ended_product_patterns"), defaults["open_ended_product_patterns"]),
        "date_time_words": _str_list(raw.get("date_time_words"), defaults["date_time_words"]),
        "more_options_phrases": _str_list(raw.get("more_options_phrases"), defaults["more_options_phrases"]),
        "composite_signals": _str_list(raw.get("composite_signals"), defaults["composite_signals"]),
        "short_answer_exclude_words": _str_list(raw.get("short_answer_exclude_words"), defaults["short_answer_exclude_words"]),
        "composite_patterns": _composite_patterns(raw.get("composite_patterns"), defaults["composite_patterns"]),
        "simple_discover_keywords": _str_list(raw.get("simple_discover_keywords"), defaults["simple_discover_keywords"]),
        "discover_with_probe_keywords": _str_list(raw.get("discover_with_probe_keywords"), defaults["discover_with_probe_keywords"]),
        "location_like_words": _str_list(raw.get("location_like_words"), defaults["location_like_words"]),
        "remove_patterns": _remove_patterns(raw.get("remove_patterns"), defaults["remove_patterns"]),
        "cat_to_label": _cat_to_label(raw.get("cat_to_label"), defaults["cat_to_label"]),
    }


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
    Uses platform_config.intent_heuristic_config (see get_intent_heuristic_config).
    """
    cfg = get_intent_heuristic_config()
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
    if any(re.search(pat, t) for pat in cfg["open_ended_product_patterns"]):
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
    if ls and any(k in ls for k in cfg["probe_keywords"]):
        if any(p in t for p in cfg["unrelated_phrases"]):
            sq, exp, proposed = _first_composite(cfg)
            for c in reversed(conv):
                if isinstance(c, dict) and c.get("role") == "user":
                    msg = (c.get("content") or "").lower()
                    for pat, queries, exp_name, plan in cfg["composite_patterns"]:
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
            sq, exp, proposed = _first_composite(cfg)
            for c in reversed(conv):
                if isinstance(c, dict) and c.get("role") == "user":
                    msg = (c.get("content") or "").lower()
                    for pat, queries, exp_name, plan in cfg["composite_patterns"]:
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
        is_date_answer = any(w in t for w in cfg["date_time_words"]) or re.search(r"\b\d{1,2}/\d{1,2}\b", t)
        budget_match = _BUDGET_RE.search(text)
        is_budget_answer = budget_match is not None
        is_short_answer = len(t.split()) <= 4 and not re.search(r"actually|forget|want\s+chocolates|want\s+flowers", t)

        if is_date_answer or is_budget_answer or is_short_answer:
            sq, exp, proposed = _first_composite(cfg)
            for c in reversed(conv):
                if isinstance(c, dict) and c.get("role") == "user":
                    msg = (c.get("content") or "").lower()
                    for pat, queries, exp_name, plan in cfg["composite_patterns"]:
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
                if not any(w in t for w in cfg["short_answer_exclude_words"]):
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
    if any(w in t for w in cfg["date_time_words"]) or re.search(r"\b\d{1,2}/\d{1,2}\b", t):
        for c in reversed(conv):
            if isinstance(c, dict) and c.get("role") == "user":
                msg = (c.get("content") or "").lower()
                if msg == t:
                    continue
                for pat, queries, exp_name, plan in cfg["composite_patterns"]:
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
    if any(p in t for p in cfg["more_options_phrases"]):
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
        if ls and any(s in ls.lower() for s in cfg["composite_signals"]):
            in_composite_context = True
        for c in conv:
            if isinstance(c, dict) and c.get("role") == "assistant" and (c.get("content") or ""):
                msg = (c.get("content") or "").lower()
                if any(s in msg for s in cfg["composite_signals"]):
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
                    for pat, _, _, _ in cfg["composite_patterns"]:
                        if re.search(pat, ucontent):
                            in_composite_context = True
                            break
                    break
        if in_composite_context:
            sq, exp, proposed = _first_composite(cfg)
            for c in reversed(conv):
                if isinstance(c, dict) and c.get("role") == "user":
                    msg = (c.get("content") or "").lower()
                    for pat, queries, exp_name, plan in cfg["composite_patterns"]:
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
    for pat, cat in cfg["remove_patterns"]:
        if re.search(pat, t):
            removed.append(cat)
    if removed:
        sq, exp, proposed = _first_composite(cfg)
        for c in reversed(conv):
            if isinstance(c, dict) and c.get("role") == "user":
                msg = (c.get("content") or "").lower()
                for pattern, queries, exp_name, plan in cfg["composite_patterns"]:
                    if re.search(pattern, msg):
                        sq, exp, proposed = list(queries), exp_name, list(plan)
                        break
                break
        removed_set = set(removed)
        sq_purged = [q for q in sq if q.lower() not in removed_set]
        label_to_key = {v.lower(): k for k, v in cfg["cat_to_label"].items()}
        proposed_purged = [lbl for lbl in proposed if label_to_key.get(lbl.lower(), lbl.lower()) not in removed_set]
        if not proposed_purged and sq_purged:
            proposed_purged = [cfg["cat_to_label"].get(q, q.capitalize()) for q in sq_purged]
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
    if len(words) <= 3 and any(w in t for w in cfg["location_like_words"]):
        for c in reversed(conv):
            if isinstance(c, dict) and c.get("role") == "user":
                msg = (c.get("content") or "").lower()
                for pat, queries, exp_name, plan in cfg["composite_patterns"]:
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

    # Simple product search: keywords that imply discover (not composite). Avoids probe for clear product intent.
    # Composite patterns take precedence; keywords and exclusions should come from config when available.
    _composite_patterns_only = [pat for pat, _, _, _ in cfg["composite_patterns"]]
    if any(kw in t for kw in cfg["simple_discover_keywords"]) and not any(re.search(pat, t) for pat in _composite_patterns_only):
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
            "recommended_next_action": "discover_products",
            "confidence_score": 0.9,
        }

    # Composite: date night, picnic, birthday party, etc. (not simple "birthday gifts")
    for pat, queries, exp_name, plan in cfg["composite_patterns"]:
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

    # Discover-with-probe: keywords that imply discover but may need probing (use config when available).
    if any(kw in t for kw in cfg["discover_with_probe_keywords"]):
        from packages.shared.discovery import derive_search_query
        derived = derive_search_query(text)
        entities = []
        budget_match = _BUDGET_RE.search(text)
        if budget_match:
            cents = int(budget_match.group(1)) * 100
            entities.append({"type": "budget", "value": cents})
        return {
            "intent_type": "discover",
            "search_query": derived or (text.strip()[:50] if text else "browse"),
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


async def _llm_resolve_intent(
    text: str,
    *,
    last_suggestion: Optional[str] = None,
    recent_conversation: Optional[List[Dict[str, Any]]] = None,
    experience_categories: Optional[List[str]] = None,
    client: Any = None,
    llm_config: Optional[Dict[str, Any]] = None,
    force_model: bool = False,
) -> Dict[str, Any]:
    """
    LLM-only path: call configured LLM for intent classification and return parsed result.
    Raises on failure (no heuristic fallback). Used by resolve_intent when LLM is configured.
    """
    if not llm_config:
        raise RuntimeError("LLM config required")
    from packages.shared.platform_llm import get_llm_chat_client, get_model_interaction_prompt
    from packages.shared.prompts import get_intent_system_prompt

    prompt_cfg = get_model_interaction_prompt(client, "intent") if client else None
    system_prompt = (prompt_cfg.get("system_prompt") if prompt_cfg else None) or get_intent_system_prompt()
    if not system_prompt:
        system_prompt = "You are an intent classifier. Return JSON: intent_type, search_query, search_queries, experience_name, bundle_options, entities, recommended_next_action, proposed_plan, confidence_score."

    provider, chat_client = get_llm_chat_client(llm_config)
    if not chat_client:
        raise RuntimeError("LLM configured but client creation failed")

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
        raise RuntimeError("Unsupported LLM provider")

    if "```" in raw:
        raw = re.sub(r"```(?:json)?\s*", "", raw)
        raw = raw.split("```")[0].strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict) or not parsed.get("intent_type"):
        raise ValueError("Invalid parsed intent")
    return parsed


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
    - Heuristic only: when LLM is not configured or has no API key.
    - LLM path: when configured; optional refinement short-circuit (heuristic) then _llm_resolve_intent; on LLM failure falls back to heuristic unless force_model=True.
    """
    from db import get_supabase
    from packages.shared.platform_llm import get_platform_llm_config

    client = get_supabase()
    llm_config = get_platform_llm_config(client) if client else None

    # Heuristic-only path when no LLM configured
    if not llm_config or not llm_config.get("api_key"):
        return _heuristic_resolve(
            text,
            last_suggestion=last_suggestion,
            recent_conversation=recent_conversation,
            probe_count=probe_count,
            thread_context=thread_context,
        )

    # Refinement short-circuit: "no limo" / "remove flowers" in composite context -> use heuristic so we get refine_composite
    intent_cfg = get_intent_heuristic_config()
    t = (text or "").strip().lower()
    for pat, _ in intent_cfg["remove_patterns"]:
        if re.search(pat, t):
            ls = (last_suggestion or "").lower()
            conv = list(recent_conversation or [])
            in_composite = any(s in ls for s in intent_cfg["composite_signals"]) or "proposed_plan" in ls
            if not in_composite and conv:
                for c in reversed(conv):
                    if isinstance(c, dict) and (c.get("role") or "").lower() == "assistant":
                        ac = (c.get("content") or "").lower()
                        if any(s in ac for s in intent_cfg["composite_signals"]):
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

    # LLM path: call LLM; on failure fall back to heuristic unless force_model
    try:
        return await _llm_resolve_intent(
            text,
            last_suggestion=last_suggestion,
            recent_conversation=recent_conversation,
            experience_categories=experience_categories,
            client=client,
            llm_config=llm_config,
            force_model=force_model,
        )
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
