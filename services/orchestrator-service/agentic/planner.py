"""
Planner module: LLM client for planning and engagement.
Resolves planner/LLM client from config; plan_next_action is provided for agentic loop integration.
"""

from typing import Any, Dict, Optional, Tuple

from packages.shared.platform_llm import get_llm_chat_client


def _get_planner_client_for_config(llm_config: Dict[str, Any]) -> Tuple[Optional[str], Any]:
    """Return (provider, client) for the given LLM config. Used by engagement and suggest_composite_bundle_options."""
    return get_llm_chat_client(llm_config)


def plan_next_action(
    user_message: str,
    state: Dict[str, Any],
    tools: Any,
    resolve_intent_fn: Any,
    discover_products_fn: Any,
    discover_composite_fn: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Stub for agentic loop. When the full loop/planner is present, this decides the next tool call.
    Raises NotImplementedError if called without a real implementation.
    """
    raise NotImplementedError(
        "plan_next_action requires the full agentic planner implementation (see run_agentic_loop)."
    )
