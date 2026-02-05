"""Progress Ledger Adaptive Card - standing intent progress with If/Then logic."""

from typing import Any, Dict, Optional

from .base import create_card, fact_set, text_block


def _format_condition(condition: Optional[Dict[str, Any]]) -> str:
    """Format condition for display. E.g. {'weather': 'sunny'} -> 'Weather == Sunny'."""
    if not condition:
        return "N/A"
    parts = [f"{k.replace('_', ' ').title()} == {str(v).title()}" for k, v in condition.items()]
    return " AND ".join(parts)


def _format_action(action: Optional[Dict[str, Any]]) -> str:
    """Format action for display. E.g. {'type': 'order', 'item': 'flowers'} -> 'Order Flowers'."""
    if not action:
        return "N/A"
    action_type = action.get("type", "").title()
    action_item = action.get("item", "")
    if action_item:
        return f"{action_type} {action_item.title()}"
    return action_type


def generate_progress_ledger_card(
    narrative: str,
    *,
    thought: Optional[str] = None,
    if_then_logic: Optional[Dict[str, Any]] = None,
    agent_reasoning: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate Progress Ledger Adaptive Card with If/Then logic visualization
    and Agent Reasoning (contextual "Why" explanations).
    """
    body = [
        text_block(narrative, weight="Bolder", size="Medium"),
    ]

    # Agent Reasoning section
    if agent_reasoning:
        body.append(
            {
                "type": "Container",
                "style": "default",
                "items": [
                    text_block("🤔 Agent Reasoning", weight="Bolder", color="Accent", size="Small"),
                    text_block(agent_reasoning, size="Small", wrap=True),
                ],
                "spacing": "Medium",
            }
        )

    # If/Then logic visualization
    if if_then_logic:
        body.append(
            {
                "type": "Container",
                "style": "emphasis",
                "items": [
                    text_block("🔍 Active Monitoring", weight="Bolder", color="Accent"),
                    fact_set(
                        [
                            {"title": "IF", "value": _format_condition(if_then_logic.get("condition"))},
                            {"title": "THEN", "value": _format_action(if_then_logic.get("action"))},
                        ]
                    ),
                ],
            }
        )

    # Thought (internal logic)
    if thought:
        body.append(
            text_block(f"💭 {thought}", size="Small", is_subtle=True),
        )

    # Context details
    if context and context.get("details"):
        body.append(
            {
                "type": "Container",
                "items": [
                    text_block("📋 Context", weight="Bolder", size="Small"),
                    fact_set(
                        [
                            {"title": key.replace("_", " ").title(), "value": str(value)}
                            for key, value in context["details"].items()
                        ]
                    ),
                ],
                "spacing": "Small",
            }
        )

    return create_card(body=body)
