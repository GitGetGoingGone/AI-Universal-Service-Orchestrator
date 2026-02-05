"""Time-Chain Adaptive Card - visual timeline of multi-leg journey."""

from typing import Any, Dict, List, Optional

from .base import create_card, fact_set, text_block


def generate_timechain_card(
    timechain: Dict[str, Any],
    *,
    legs: Optional[List[Dict[str, Any]]] = None,
    show_conflicts: bool = False,
) -> Dict[str, Any]:
    """
    Generate Adaptive Card for multi-leg journey timeline.
    Visual timeline with ETA, deadlines, and optional conflict indicators.
    """
    body = [
        text_block("Journey Timeline", size="Large", weight="Bolder"),
        text_block(timechain.get("description", "Your multi-leg order timeline."), size="Small") if timechain.get("description") else None,
    ]
    body = [b for b in body if b]

    # Summary
    facts = []
    if timechain.get("total_duration"):
        facts.append({"title": "Total Duration", "value": str(timechain["total_duration"])})
    if timechain.get("leg_count"):
        facts.append({"title": "Legs", "value": str(timechain["leg_count"])})
    if timechain.get("status"):
        facts.append({"title": "Status", "value": str(timechain["status"]).title()})
    if facts:
        body.append(fact_set(facts))

    # Legs (timeline)
    leg_list = legs or timechain.get("legs", [])
    for i, leg in enumerate(leg_list):
        leg_name = leg.get("name", f"Leg {i + 1}")
        eta = leg.get("eta") or leg.get("arrival_time", "—")
        deadline = leg.get("deadline")
        has_conflict = leg.get("has_conflict", False) and show_conflicts

        items = [
            text_block(f"{i + 1}. {leg_name}", weight="Bolder"),
            text_block(f"ETA: {eta}", size="Small"),
        ]
        if deadline:
            items.append(text_block(f"Deadline: {deadline}", size="Small", is_subtle=True))
        if has_conflict:
            items.insert(1, text_block("⚠️ Conflict risk", size="Small", color="Attention"))

        body.append(
            {
                "type": "Container",
                "style": "emphasis" if has_conflict else "default",
                "items": items,
            }
        )

    actions = [
        {"type": "Action.Submit", "title": "View Details", "data": {"action": "view_timechain", "timechain_id": str(timechain.get("id", ""))}},
    ]

    return create_card(body=body, actions=actions)
