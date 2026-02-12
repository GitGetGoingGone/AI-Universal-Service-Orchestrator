"""Agentic decision loop: Observe → Reason → Plan → Execute → Reflect."""

import logging
from typing import Any, Dict, Optional

from .planner import plan_next_action
from .tools import execute_tool

logger = logging.getLogger(__name__)


async def run_agentic_loop(
    user_message: str,
    *,
    user_id: Optional[str] = None,
    limit: int = 20,
    resolve_intent_fn=None,
    discover_products_fn=None,
    start_orchestration_fn=None,
    create_standing_intent_fn=None,
    use_agentic: bool = True,
    max_iterations: int = 5,
    platform: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the agentic decision loop until completion.

    If use_agentic=False or planner fails, falls back to direct intent→discover flow.
    """
    if not use_agentic:
        return await _direct_flow(
            user_message,
            user_id=user_id,
            limit=limit,
            resolve_intent_fn=resolve_intent_fn,
            discover_products_fn=discover_products_fn,
        )

    state = {
        "messages": [],
        "last_tool_result": None,
        "iteration": 0,
        "agent_reasoning": [],
    }

    intent_data = None
    products_data = None
    adaptive_card = None
    machine_readable = None

    for iteration in range(max_iterations):
        state["iteration"] = iteration

        plan = await plan_next_action(user_message, state, max_iterations=max_iterations)

        if plan.get("action") == "complete":
            state["agent_reasoning"].append(plan.get("reasoning", ""))
            break

        if plan.get("action") == "tool":
            tool_name = plan["tool_name"]
            tool_args = plan.get("tool_args", {})
            state["agent_reasoning"].append(plan.get("reasoning", ""))

            # Inject limit and location from intent entities for discover_products
            if tool_name == "discover_products":
                tool_args = dict(tool_args)
                tool_args.setdefault("limit", limit)
                if intent_data:
                    loc = _extract_location(intent_data)
                    if loc:
                        tool_args.setdefault("location", loc)

            if tool_name == "create_standing_intent":
                tool_args = dict(tool_args)
                tool_args.setdefault("platform", platform)
                tool_args.setdefault("thread_id", thread_id)

            result = await execute_tool(
                tool_name,
                tool_args,
                resolve_intent_fn=resolve_intent_fn,
                discover_products_fn=discover_products_fn,
                start_orchestration_fn=start_orchestration_fn,
                create_standing_intent_fn=create_standing_intent_fn,
            )

            state["last_tool_result"] = result

            if "error" in result:
                state["agent_reasoning"].append(f"Tool error: {result['error']}")
                state["last_error"] = result["error"]
                break

            if tool_name == "resolve_intent":
                intent_data = result.get("data", result)
            elif tool_name == "discover_products":
                products_data = result.get("data", result)
                adaptive_card = result.get("adaptive_card")
                machine_readable = result.get("machine_readable")
            elif tool_name == "create_standing_intent":
                intent_data = intent_data or {}
                intent_data["standing_intent"] = result

            if tool_name == "complete":
                break

    # Build final response
    return _build_response(
        intent_data=intent_data,
        products_data=products_data,
        adaptive_card=adaptive_card,
        machine_readable=machine_readable,
        agent_reasoning=state.get("agent_reasoning", []),
        user_message=user_message,
        error=state.get("last_error"),
    )


async def _direct_flow(
    user_message: str,
    *,
    user_id: Optional[str] = None,
    limit: int = 20,
    resolve_intent_fn=None,
    discover_products_fn=None,
) -> Dict[str, Any]:
    """Direct flow without agentic planning (original intent → discover)."""
    if not resolve_intent_fn or not discover_products_fn:
        return {"error": "Services not configured"}

    intent_response = await resolve_intent_fn(user_message)
    intent_data = intent_response.get("data", intent_response)
    intent_type = intent_data.get("intent_type", "unknown")
    # Empty/generic → "browse" (Discovery returns sample products)
    search_query = intent_data.get("search_query") or "browse"

    products_data = None
    adaptive_card = None
    machine_readable = None

    if intent_type == "discover":
        location = _extract_location(intent_data)
        discovery_response = await discover_products_fn(
            query=search_query,
            limit=limit,
            location=location,
        )
        products_data = discovery_response.get("data", discovery_response)
        adaptive_card = discovery_response.get("adaptive_card")
        machine_readable = discovery_response.get("machine_readable")

    return _build_response(
        intent_data=intent_data,
        products_data=products_data,
        adaptive_card=adaptive_card,
        machine_readable=machine_readable,
        agent_reasoning=[],
        user_message=user_message,
    )


def _extract_location(intent_data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Extract location from intent entities."""
    if not intent_data:
        return None
    for e in intent_data.get("entities", []):
        if isinstance(e, dict) and e.get("type") == "location":
            return str(e.get("value", "")) or None
    return None


def _build_response(
    *,
    intent_data: Optional[Dict[str, Any]] = None,
    products_data: Optional[Dict[str, Any]] = None,
    adaptive_card: Optional[Dict[str, Any]] = None,
    machine_readable: Optional[Dict[str, Any]] = None,
    agent_reasoning: Optional[list] = None,
    user_message: str = "",
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Build unified chat response."""
    intent_data = intent_data or {}
    search_query = intent_data.get("search_query") or user_message[:100]

    mr = {
        "@context": "https://schema.org",
        "@type": "ChatOrchestrationResult",
        "intent": {
            "@type": "Intent",
            "intentType": intent_data.get("intent_type", "unknown"),
            "searchQuery": search_query,
            "confidenceScore": intent_data.get("confidence_score"),
        },
        "products": machine_readable,
    }
    if agent_reasoning:
        mr["agentReasoning"] = agent_reasoning

    out = {
        "data": {
            "intent": intent_data,
            "products": products_data,
        },
        "machine_readable": mr,
        "adaptive_card": adaptive_card,
        "agent_reasoning": agent_reasoning or [],
    }
    if error:
        out["data"]["error"] = error
        out["error"] = error
    return out
