"""Conflict Suggestion Adaptive Card - proactive alternatives when conflicts detected."""

from typing import Any, Dict, List, Optional

from .base import create_card, fact_set, text_block


def generate_conflict_suggestion_card(
    conflict: Dict[str, Any],
    *,
    suggestions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generate Adaptive Card when Time-Chain conflict is detected.
    Shows delay impact and proactive alternatives (e.g. courier separately).
    """
    body = [
        text_block("⚠️ Conflict Detected", weight="Bolder", color="Attention"),
        text_block(
            conflict.get("message", "Adding this item may cause a scheduling conflict."),
            wrap=True,
        ),
    ]

    # Conflict facts
    facts = []
    if conflict.get("delay_minutes") is not None:
        facts.append({"title": "Delay", "value": f"{int(conflict['delay_minutes'])} minutes"})
    if conflict.get("affected_leg"):
        facts.append({"title": "Affected", "value": str(conflict["affected_leg"])})
    if conflict.get("deadline"):
        facts.append({"title": "Deadline", "value": str(conflict["deadline"])})
    if conflict.get("new_arrival_time"):
        facts.append({"title": "New ETA", "value": str(conflict["new_arrival_time"])})
    if facts:
        body.append(fact_set(facts))

    # Suggestions (alternatives)
    suggestion_list = suggestions or conflict.get("suggestions", [])
    if suggestion_list:
        body.append(text_block("Alternatives", size="Medium", weight="Bolder"))
        for sug in suggestion_list:
            msg = sug.get("message", sug.get("description", ""))
            alt = sug.get("alternative", {})
            cost = alt.get("estimated_cost")
            cost_str = f" (${cost:.2f})" if cost is not None else ""
            body.append(
                {
                    "type": "Container",
                    "style": "emphasis",
                    "items": [
                        text_block(msg, wrap=True),
                        text_block(f"Option: {alt.get('type', 'alternative').replace('_', ' ').title()}{cost_str}", size="Small") if alt else None,
                    ],
                    "actions": [
                        {
                            "type": "Action.Submit",
                            "title": sug.get("action_title", "Choose this"),
                            "data": {"action": sug.get("action", "choose_alternative"), "suggestion_id": str(sug.get("id", ""))},
                        },
                    ],
                }
            )
            body[-1]["items"] = [i for i in body[-1]["items"] if i]

    actions = [
        {"type": "Action.Submit", "title": "Proceed Anyway", "data": {"action": "proceed", "conflict_id": str(conflict.get("id", ""))}},
    ]

    # Add suggestion-specific actions (e.g. "Courier Separately")
    for sug in suggestion_list[:2]:
        action_title = sug.get("action_title", "")
        if "Courier" in action_title or "Separate" in action_title:
            cost = sug.get("alternative", {}).get("estimated_cost")
            title = f"{action_title} (${cost:.2f})" if cost is not None else action_title
            actions.append(
                {"type": "Action.Submit", "title": title, "data": {"action": "separate_delivery", "suggestion_id": str(sug.get("id", ""))}}
            )
            break

    return create_card(body=body, actions=actions)
