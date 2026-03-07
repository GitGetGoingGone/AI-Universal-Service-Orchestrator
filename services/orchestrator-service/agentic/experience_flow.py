"""
Config-driven experience flow: date/area probing and narrative instructions.

Rules are stored in platform_config.composite_discovery_config.experience_flow_rules.
Each rule can match by experience_keywords (substring in experience_name or search_queries)
and define:
  - skip_date_area_probe: if True, do not require date/location before calling discover_composite
  - no_products_instruction: custom prompt fragment when no products are shown yet (themed options)

Example (add to composite_discovery_config.experience_flow_rules in platform_config):
  [
    {
      "experience_keywords": ["gift", "custom gift"],
      "skip_date_area_probe": true,
      "no_products_instruction": "User asked for gift ideas. Present the themed options above and invite them to pick one so you can show product options. Do NOT ask for date or area/downtown. Only ask for delivery address when they are ready to add to bundle or checkout."
    }
  ]
New bundle or experience types: add another object to the list; no code changes required.
"""

from typing import Any, Dict, List, Optional


def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def _intent_text_for_match(intent_data: Dict[str, Any]) -> str:
    """Single string from experience_name + search_queries for keyword matching."""
    exp = _normalize(intent_data.get("experience_name") or "")
    sq = intent_data.get("search_queries") or []
    if not isinstance(sq, list):
        sq = []
    sq_str = " ".join(_normalize(str(q)) for q in sq if q)
    return f"{exp} {sq_str}".strip()


def match_intent_to_rule(intent_data: Dict[str, Any], rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Return the first rule whose experience_keywords match the intent.
    intent_data: dict with experience_name, search_queries.
    rules: list of { experience_keywords: [...], skip_date_area_probe?: bool, no_products_instruction?: str }.
    """
    if not rules or not intent_data:
        return None
    text = _intent_text_for_match(intent_data)
    if not text:
        return None
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        keywords = rule.get("experience_keywords")
        if not isinstance(keywords, list):
            continue
        for kw in keywords:
            if kw and _normalize(str(kw)) in text:
                return rule
    return None


def should_skip_date_area_probe(intent_data: Dict[str, Any], rules: List[Dict[str, Any]]) -> bool:
    """
    True if a matching rule has skip_date_area_probe true.
    Used by planner to avoid requiring date/area before discover_composite.
    """
    rule = match_intent_to_rule(intent_data, rules)
    return bool(rule and rule.get("skip_date_area_probe") is True)


def get_no_products_instruction(intent_data: Dict[str, Any], rules: List[Dict[str, Any]]) -> Optional[str]:
    """
    Return custom no-products narrative instruction if a matching rule defines it.
    Otherwise None (caller uses default copy).
    """
    rule = match_intent_to_rule(intent_data, rules)
    if not rule:
        return None
    instruction = rule.get("no_products_instruction")
    if instruction is None or (isinstance(instruction, str) and not instruction.strip()):
        return None
    return instruction.strip()
