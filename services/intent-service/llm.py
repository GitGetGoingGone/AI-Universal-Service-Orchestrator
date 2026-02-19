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

# Composite experience patterns -> (search_queries, experience_name)
_COMPOSITE_PATTERNS = [
    (r"date\s*night|plan\s*a\s*date|romantic\s*evening", ["flowers", "dinner", "limo"], "date night"),
    (r"birthday\s*party|birthday\s*celebration", ["cake", "flowers", "gifts"], "birthday party"),
    (r"picnic", ["basket", "blanket", "food"], "picnic"),
    (r"baby\s*shower", ["cake", "decorations", "gifts"], "baby shower"),
]

# Budget extraction: "under $50", "$50", "50 dollars"
_BUDGET_RE = re.compile(r"(?:under|under\s+)?\$?\s*(\d+)\s*(?:dollars?|dollars?|bucks?)?", re.I)


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
            for c in reversed(conv):
                if isinstance(c, dict) and c.get("role") == "user":
                    msg = (c.get("content") or "").lower()
                    for pat, queries, exp_name in _COMPOSITE_PATTERNS:
                        if re.search(pat, msg):
                            sq, exp = queries, exp_name
                            break
                    break
            return {
                "intent_type": "discover_composite",
                "search_query": " ".join(sq),
                "search_queries": sq,
                "experience_name": exp,
                "bundle_options": [{"label": exp, "categories": sq}],
                "entities": [],
                "unrelated_to_probing": True,
                "recommended_next_action": "discover_composite",
                "confidence_score": 0.85,
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
            for c in reversed(conv):
                if isinstance(c, dict) and c.get("role") == "user":
                    msg = (c.get("content") or "").lower()
                    for pat, queries, exp_name in _COMPOSITE_PATTERNS:
                        if re.search(pat, msg):
                            sq, exp = queries, exp_name
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
                "recommended_next_action": "discover_composite",
                "confidence_score": 0.9,
            }

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
    for pat, queries, exp_name in _COMPOSITE_PATTERNS:
        if re.search(pat, t):
            return {
                "intent_type": "discover_composite",
                "search_query": " ".join(queries),
                "search_queries": queries,
                "experience_name": exp_name,
                "bundle_options": [{"label": exp_name, "categories": queries}],
                "entities": [],
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
    user_content += "\n\nReturn valid JSON only."

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
