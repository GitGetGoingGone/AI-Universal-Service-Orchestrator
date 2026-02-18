"""LLM-based planner for Agentic AI - decides next action from state."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from .tools import TOOL_DEFS

logger = logging.getLogger(__name__)

PLANNER_SYSTEM = """You are an agentic AI assistant for a multi-vendor order platform. You help users discover products, create bundles, and manage orders.

Given the current state (user message, previous actions, results, last_suggestion, recent_conversation), decide the next action.

Goal for composite experiences (date night, etc.): Get date/time and kind of date from the user. When we don't have that info, assume today or tomorrow and no dietary constraints—proceed with discover_composite using these defaults.

Rules:
- For a NEW user message: first call resolve_intent to understand what they want.
- If intent is "browse" (user said hi, show me, what do you have, etc.): ALWAYS call complete with a friendly opener. Do NOT call discover_products. Example: "We have so much to show! It would help if you tell me what kind of things you're looking for—gifts, flowers, chocolates, experiences, or something else?" Only call discover_products after the user has provided at least one category or preference.
- If intent is "discover" (single category like chocolates, flowers): PREFER probing first. When the user message is generic (e.g. "show me chocolates", "chocolates", "flowers" with no preferences, occasion, budget, or add-ons), call complete with 1-2 friendly questions (e.g. "Any preferences? Occasion? Budget? Would you like to add something like flowers with that?"). Only call discover_products when the user has provided details or explicitly asks for options.
- If intent is "discover_composite" (e.g. date night, birthday party): PREFER probing first. When the user message is generic (e.g. "plan a date night", "date night" with no date, budget, or preferences), call complete with 1-2 friendly questions (e.g. "What date? Any dietary preferences? Budget?"). Only call discover_composite when the user has provided details or explicitly asks for options. When discover_composite returns products, prefer the best combination for the experience (e.g. date night: flowers + dinner + movie). After 2+ probing rounds (probe_count >= 2), make assumptions (today/tomorrow, no dietary constraints) and call discover_composite—do not ask again.
- CRITICAL: When intent has unrelated_to_probing (user said "show more options", "other options", etc. instead of answering our questions): call complete with a message that handles it gracefully. Either (a) rephrase the question in a different way, or (b) offer to proceed with default assumptions (this weekend, no dietary restrictions). Example: "I'd be happy to show you options! I can suggest a classic date night for this weekend—or if you have a specific date in mind, let me know. Should I show you some ideas?" Never return "Done." or empty when unrelated_to_probing.
- CRITICAL: When last_suggestion or recent_conversation shows we asked probing questions and the user NOW provides details, you MUST fetch products. For composite (date night, etc.): call discover_composite. For single category (chocolates, flowers, etc.): call discover_products. NEVER complete with "Done" or empty when the user has answered our questions—fetch products first.
- When last_suggestion exists and user refines (e.g. "I don't want flowers, add a movie", "no flowers", "add chocolates instead"): resolve_intent will interpret the refinement. Use the new search_query from intent. For composite experiences, the intent may return updated search_queries.
- If intent is checkout/track/support: use track_order when user asks about order status. CRITICAL: When thread_context has order_id, call track_order with that order_id—NEVER ask the user for order ID. The thread already has it.
- For standing intents (condition-based, delayed, "notify me when"): use create_standing_intent.
- For other long-running workflows: use start_orchestration.
- Call "complete" when you have a response ready for the user (e.g. probing questions, or products already fetched).
- Prefer completing in one or two tool calls when possible.
- Extract location from "around me" or "near X" for discover_products when relevant.
- External factors (REQUIRED for composite experiences): ALWAYS check weather and events when the user provides or implies a location for experiences (date night, picnic, etc.). Call get_weather and get_upcoming_occasions for the location BEFORE calling discover_composite or before completing with probing. When the user gives a flexible date (e.g. "anytime next week", "this weekend", "sometime next week"), use web_search with "weather forecast [location] [timeframe]" to get multi-day outlook. Use this data to suggest optimal dates: e.g. "Wednesday looks best for outdoor plans—clear skies" or "Avoid Friday near downtown due to the football game crowd." Incorporate these suggestions into your complete message so the user gets the best experience.
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

    state_summary = {
        "iteration": state.get("iteration", 0),
        "probe_count": state.get("probe_count", 0),
        "last_tool_result": state.get("last_tool_result"),
        "last_suggestion": state.get("last_suggestion"),
        "recent_conversation": recent_conversation[-4:] if recent_conversation else None,
        "thread_context": thread_context if thread_context else None,
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

        if intent_type == "discover" and search_query:
            return {
                "action": "tool",
                "tool_name": "discover_products",
                "tool_args": tool_args,
                "reasoning": "Intent is discover, fetching products.",
            }

        if intent_type == "discover_composite":
            # Probe first: generic "plan a date night" with no details -> ask questions
            has_details = any(
                e.get("type") in ("location", "budget")
                for e in intent_data.get("entities", [])
                if isinstance(e, dict)
            )
            if not has_details and not any(
                w in (user_message or "").lower()
                for w in ("$", "dollar", "vegetarian", "vegan", "dallas", "nyc", "budget", "around", "casual", "romantic")
            ):
                return {
                    "action": "complete",
                    "message": "I'd love to help you plan a perfect date night! To tailor the experience, could you tell me: 1) What date are you planning for? 2) Do you have a budget in mind? 3) Any dietary preferences? 4) Preferred location or area?",
                    "reasoning": "Probing for date night details before fetching.",
                }
            sq = intent_data.get("search_queries") or ["flowers", "dinner", "movies"]
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
                "reasoning": "Intent is discover_composite, fetching products.",
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
