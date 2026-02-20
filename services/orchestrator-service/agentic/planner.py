"""LLM-based planner for Agentic AI - decides next action from state."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from .tools import TOOL_DEFS

logger = logging.getLogger(__name__)

PLANNER_SYSTEM = """You are the Agentic Orchestrator. Decide the next tool.

Rule 1: Read Admin Config. If ucp_prioritized is true in state, call fetch_ucp_manifest first before discover_products or discover_composite.

Rule 2: For outdoor/location-based experiences (date night, picnic, etc.), ALWAYS call get_weather and get_upcoming_occasions for the location BEFORE calling discover_composite. Use this data to pivot the plan if necessary (e.g., rain -> suggest "Indoor Dining" instead of "Picnic"). Update the proposed_plan in your reasoning so the frontend Draft Itinerary reflects the pivot.

Rule 3 (Halt & Preview): Do NOT execute discover_composite if location or time is missing. Instead call complete with ONE short concierge message. Use state.proposed_plan and state.entities to acknowledge what the user already gave (e.g. "Today it is! I'm planning your Flowers and Dinner for Downtown. What neighborhood are we looking at?") — never repeat the full 4-question list. The frontend receives proposed_plan as the Draft Itinerary (checklist) while you probe.

Rule 4 (browse / open-ended): For intent browse or generic queries (e.g. "what products do you have", "what do you have", "show me options"), call complete with ONE short message that probes for the EXPERIENCE they want to explore. Examples: "What kind of experience are you looking for—something romantic, a celebration, a gift, or maybe a date night? I can suggest themed bundles once I know." Do NOT list all product categories; do NOT call discover_products or discover_composite until the user indicates an experience. For intent discover/discover_composite (when they already named an experience), when user has provided location and time (or date), call discover_composite; when they have not, call complete with the short probe above (Rule 3).

Rule 5: When last_suggestion shows probing questions and user NOW provides details, you MUST fetch products. Never complete with "Done" when user answered our questions.

Additional rules:
- For a NEW user message: first call resolve_intent to understand what they want.
- If intent is checkout/track/support: use track_order when user asks about order status. CRITICAL: When thread_context has order_id, call track_order with that order_id—NEVER ask the user for order ID.
- For standing intents: use create_standing_intent. For other long-running workflows: use start_orchestration.
- When intent has unrelated_to_probing: call complete with a graceful message (rephrase or offer default assumptions).
- When user refines (e.g. "no flowers, add a movie"): resolve_intent interprets it. Use the new search_query.
- Extract location from "around me" or "near X" for discover_products when relevant.
- When user gives flexible date (e.g. "anytime next week"), use web_search for weather outlook and suggest optimal dates.
- Metadata: The intent's proposed_plan is passed to the frontend as the Draft Itinerary; ensure your complete message references it (e.g. "your Flowers and Dinner") so the user sees we're building that plan.
- Refinement leak: When intent is refine_composite with removed_categories, use the intent's already-purged search_queries and proposed_plan for discover_composite; do not re-add removed categories.
- Variety leak: When the user asks for "other options" or "show me something else", the intent sets request_variety; the loop will set rotate_tier so the Partner Balancer shows a different tier first. Proceed with discover_composite (or complete with options) as normal.
"""


def _get_planner_client_for_config(llm_config: Dict[str, Any]):
    """Get planner client from platform config (llm_providers). No env fallback."""
    from openai import OpenAI

    cfg = llm_config or {}
    preferred = cfg.get("provider", "azure")
    if preferred == "openai":
        preferred = "azure"
    api_key = cfg.get("api_key")
    endpoint = cfg.get("endpoint")

    if preferred == "openrouter" and api_key:
        return ("openrouter", OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key))

    if preferred == "custom" and endpoint and api_key:
        base = endpoint.rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        return ("custom", OpenAI(base_url=base, api_key=api_key))

    if preferred == "gemini" and api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            return ("gemini", genai)
        except ImportError:
            logger.warning("google-generativeai not installed for Gemini support.")

    if preferred in ("azure", "openai") and endpoint and api_key:
        from openai import AzureOpenAI
        return ("azure", AzureOpenAI(
            api_key=api_key,
            api_version="2024-02-01",
            azure_endpoint=endpoint.rstrip("/"),
        ))

    return (None, None)


async def plan_next_action(
    user_message: str,
    state: Dict[str, Any],
    *,
    max_iterations: int = 5,
    llm_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Use LLM to plan and execute next action. Returns final result or intermediate state.

    state: {
        "messages": [...],  # conversation history
        "last_tool_result": {...},  # result of last tool call
        "iteration": int,
    }
    llm_config: Optional override from platform_config. When None, fetched via get_llm_config().
    """
    if llm_config is None:
        from api.admin import get_llm_config
        llm_config = get_llm_config()

    provider, client = _get_planner_client_for_config(llm_config)
    if not client:
        logger.info("Planner: No LLM client (provider=%s), using fallback", provider)
        return _fallback_plan(user_message, state)

    model = llm_config.get("model") or "gpt-4o"
    temperature = float(llm_config.get("temperature", 0.1))
    temperature = max(0.0, min(1.0, temperature))

    # Build prompt with current state (user message, prior results, last_suggestion, recent conversation)
    messages = state.get("messages") or []
    recent_conversation = []
    for m in messages[-4:]:  # Last 2 exchanges (user + assistant)
        if isinstance(m, dict) and m.get("content"):
            role = m.get("role", "unknown")
            content = str(m.get("content", ""))[:300]
            recent_conversation.append(f"{role}: {content}")
    thread_context = {}
    if state.get("order_id"):
        thread_context["order_id"] = state["order_id"]
    if state.get("bundle_id"):
        thread_context["bundle_id"] = state["bundle_id"]

    # Intent Preview: pass proposed_plan, experience_name, entities so planner can write concierge probe message
    intent_from_result = None
    last_result = state.get("last_tool_result")
    if last_result and isinstance(last_result, dict):
        data = last_result.get("data", last_result)
        if isinstance(data, dict) and data.get("intent_type"):
            intent_from_result = data
    state_summary = {
        "iteration": state.get("iteration", 0),
        "probe_count": state.get("probe_count", 0),
        "last_tool_result": state.get("last_tool_result"),
        "last_suggestion": state.get("last_suggestion"),
        "recent_conversation": recent_conversation[-4:] if recent_conversation else None,
        "thread_context": thread_context if thread_context else None,
        "ucp_prioritized": state.get("ucp_prioritized", False),
        "proposed_plan": (intent_from_result or {}).get("proposed_plan"),
        "experience_name": (intent_from_result or {}).get("experience_name"),
        "entities": (intent_from_result or {}).get("entities") or [],
    }
    user_content = f"User message: {user_message}\n\nCurrent state: {json.dumps(state_summary, default=str)[:1800]}"

    # Use admin-configured planner prompt from DB when available and enabled
    planner_prompt = PLANNER_SYSTEM
    try:
        from db import get_supabase
        from packages.shared.platform_llm import get_model_interaction_prompt
        client = get_supabase()
        prompt_cfg = get_model_interaction_prompt(client, "planner") if client else None
        if prompt_cfg and prompt_cfg.get("enabled", True):
            db_prompt = (prompt_cfg.get("system_prompt") or "").strip()
            if db_prompt:
                planner_prompt = db_prompt
    except Exception:
        pass

    try:
        if provider in ("azure", "openrouter", "custom"):
            messages = [
                {"role": "system", "content": planner_prompt},
                {"role": "user", "content": user_content},
            ]
            tools = [{"type": "function", "function": t} for t in TOOL_DEFS]

            response = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=temperature,
                    max_tokens=500,
                )
            )
            choice = response.choices[0]
            msg = choice.message

            if msg.tool_calls:
                tool_call = msg.tool_calls[0]
                name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                return {
                    "action": "tool",
                    "tool_name": name,
                    "tool_args": args,
                    "reasoning": msg.content or "",
                }

            return {
                "action": "complete",
                "message": msg.content or "Done.",
                "reasoning": msg.content or "",
            }

        if provider == "gemini":
            return await _plan_with_gemini(client, user_content, model=model, temperature=temperature, system_prompt=planner_prompt)
    except Exception as e:
        logger.warning("Planner LLM failed: %s", e)
        return _fallback_plan(user_message, state)

    return _fallback_plan(user_message, state)


async def _plan_with_gemini(
    genai_module,
    user_content: str,
    *,
    model: str,
    temperature: float = 0.1,
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Use Gemini for planning (function calling). Requires google-generativeai."""
    from .tools import TOOL_DEFS

    declarations = []
    for t in TOOL_DEFS:
        declarations.append({
            "name": t["name"],
            "description": t.get("description", ""),
            "parameters": t.get("parameters", {"type": "object", "properties": {}}),
        })

    gen_model = genai_module.GenerativeModel(
        model,
        tools=[{"function_declarations": declarations}],
    )

    prompt = f"{system_prompt or PLANNER_SYSTEM}\n\n{user_content}"

    def _call():
        resp = gen_model.generate_content(
            prompt,
            generation_config={"temperature": temperature, "max_output_tokens": 500},
        )
        return resp

    response = await asyncio.to_thread(_call)

    if not response.candidates:
        return {"action": "complete", "message": "Done.", "reasoning": ""}

    parts = response.candidates[0].content.parts if response.candidates[0].content else []
    for part in parts:
        if hasattr(part, "function_call") and part.function_call:
            fc = part.function_call
            name = getattr(fc, "name", "")
            args = dict(getattr(fc, "args", {})) if hasattr(fc, "args") else {}
            return {
                "action": "tool",
                "tool_name": name,
                "tool_args": args,
                "reasoning": getattr(part, "text", "") or "",
            }

    text = response.text if hasattr(response, "text") else "Done."
    return {"action": "complete", "message": text, "reasoning": text}


def _fallback_plan(user_message: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback when LLM is not configured: always resolve_intent then discover if needed."""
    iteration = state.get("iteration", 0)
    last_result = state.get("last_tool_result")

    if iteration == 0:
        return {
            "action": "tool",
            "tool_name": "resolve_intent",
            "tool_args": {"text": user_message},
            "reasoning": "Resolving intent from user message.",
        }

    if last_result and iteration == 1:
        intent_data = last_result.get("data", last_result)
        intent_type = intent_data.get("intent_type", "unknown")
        search_query = intent_data.get("search_query") or user_message[:100]
        tool_args = {"query": search_query, "limit": 20}
        for e in intent_data.get("entities", []):
            if isinstance(e, dict) and e.get("type") == "location":
                tool_args["location"] = str(e.get("value", ""))
                break

        if intent_type == "discover":
            rec = intent_data.get("recommended_next_action", "")
            if rec == "complete_with_probing" and ("gift" in (search_query or "").lower() or "birthday" in (user_message or "").lower() or "baby" in (user_message or "").lower()):
                return {
                    "action": "complete",
                    "message": "I'd love to help you find the perfect gift! To tailor my suggestions, could you tell me: 1) Who is it for—age or relationship? 2) Boy, girl, or neutral? 3) Any interests—experiences, movies, books, games, or something tangible?",
                    "reasoning": "Probing for gift details (age, recipient, interests) before fetching.",
                }
            if search_query:
                return {
                    "action": "tool",
                    "tool_name": "discover_products",
                    "tool_args": tool_args,
                    "reasoning": "Intent is discover, fetching products.",
                }

        if intent_type in ("discover_composite", "refine_composite"):
            # Refinement leak: use purged search_queries and proposed_plan from intent (removed_categories already applied)
            if intent_type == "refine_composite" and intent_data.get("removed_categories"):
                sq = intent_data.get("search_queries") or ["flowers", "dinner", "limo"]
                proposed_plan = intent_data.get("proposed_plan") or ["Flowers", "Dinner", "Limo"]
            else:
                sq = intent_data.get("search_queries") or ["flowers", "dinner", "movies"]
                proposed_plan = intent_data.get("proposed_plan") or ["Flowers", "Dinner", "Limo"]
            # Halt & Preview: if location or time missing, complete with ONE short concierge message (not 4-question list)
            entities = intent_data.get("entities") or []
            has_location = any(
                isinstance(e, dict) and (e.get("type") or "").lower() == "location" and e.get("value")
                for e in entities
            )
            has_time = any(
                isinstance(e, dict) and (e.get("type") or "").lower() in ("time", "date") and e.get("value")
                for e in entities
            )
            has_budget = any(
                isinstance(e, dict) and (e.get("type") or "").lower() == "budget" and e.get("value")
                for e in entities
            )
            plan_str = " and ".join(proposed_plan) if proposed_plan else "your experience"
            exp_name = intent_data.get("experience_name") or "date night"
            loc_val = next((e.get("value") for e in entities if isinstance(e, dict) and (e.get("type") or "").lower() == "location"), None)
            time_val = next((e.get("value") for e in entities if isinstance(e, dict) and (e.get("type") or "").lower() in ("time", "date")), None)
            if not has_location or not has_time:
                # Concierge-style one-liner: acknowledge what we have, ask for the next missing piece
                if has_time and has_location:
                    pass  # fall through to discover_composite
                elif has_time and loc_val:
                    pass
                else:
                    if time_val and loc_val:
                        msg = f"Today it is! I'm planning your {plan_str} for {loc_val}. What neighborhood or area should I focus on?"
                    elif time_val:
                        msg = f"Today it is! I'm planning your {plan_str}. What neighborhood or area are we looking at?"
                    elif loc_val:
                        msg = f"I'm planning your {plan_str} for {loc_val}. What date are you thinking?"
                    else:
                        msg = f"I'd love to help you plan a perfect {exp_name}! I'm thinking {plan_str}. What date are you planning for, and which area — e.g. downtown or a neighborhood?"
                    return {
                        "action": "complete",
                        "message": msg,
                        "reasoning": "Halt & Preview: location or time missing; concierge probe with proposed_plan.",
                    }
            exp_name = intent_data.get("experience_name") or "experience"
            loc = None
            for e in intent_data.get("entities", []):
                if isinstance(e, dict) and e.get("type") == "location":
                    loc = str(e.get("value", "")) or None
                    break
            return {
                "action": "tool",
                "tool_name": "discover_composite",
                "tool_args": {
                    "search_queries": sq,
                    "experience_name": exp_name,
                    "location": loc,
                },
                "reasoning": "Intent is discover_composite or refine_composite (purged categories), fetching products.",
            }

    # When we have products from a prior tool (iteration >= 2), return empty message
    # so chat uses generate_engagement_response instead of generic "Processed your request."
    if iteration >= 2 and last_result:
        data = last_result.get("data", last_result)
        if data.get("products") or data.get("categories"):
            return {
                "action": "complete",
                "message": "",
                "reasoning": "",
            }

    return {
        "action": "complete",
        "message": "Processed your request.",
        "reasoning": "",
    }
