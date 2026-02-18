"""Rules layer: upsell, surge, and promo rules. Consumes intent + context, returns addon/surge/promo decisions."""

from typing import Any, Dict, List


def evaluate_upsell_surge_rules(
    intent_data: Dict[str, Any],
    rules_config: Dict[str, Any],
    *,
    bundle_item_count: int = 0,
) -> Dict[str, Any]:
    """
    Evaluate upsell, surge, and promo rules against intent and context.
    Returns addon_categories, boost_addons, apply_surge, surge_pct, promo_products, upsell_suggestions.
    """
    out: Dict[str, Any] = {
        "addon_categories": [],
        "boost_addons": False,
        "apply_surge": False,
        "surge_pct": 0,
        "promo_products": [],
        "upsell_suggestions": None,
    }

    if not rules_config or not rules_config.get("enabled", False):
        return out

    intent_type = intent_data.get("intent_type", "")
    entities = intent_data.get("entities") or []
    search_queries = intent_data.get("search_queries") or []
    search_query = (intent_data.get("search_query") or "").lower()
    experience_name = (intent_data.get("experience_name") or "").lower()
    purchase_intent = intent_data.get("purchase_intent", "exploring")
    urgency_signals = intent_data.get("urgency_signals") or []

    # Upsell rules
    for rule in rules_config.get("upsell_rules") or []:
        if _match_upsell_rule(rule, intent_type, experience_name, purchase_intent, search_queries, search_query):
            cats = rule.get("addon_categories") or []
            out["addon_categories"] = list(dict.fromkeys(out["addon_categories"] + cats))
            if rule.get("boost_in_results"):
                out["boost_addons"] = True

    # Surge rules
    for rule in rules_config.get("surge_rules") or []:
        if _match_surge_rule(rule, intent_type, purchase_intent, urgency_signals):
            out["apply_surge"] = True
            pct = rule.get("surge_pct", 0)
            if pct > out["surge_pct"]:
                out["surge_pct"] = pct
            max_pct = rule.get("max_surge_pct")
            if max_pct is not None and out["surge_pct"] > max_pct:
                out["surge_pct"] = max_pct

    # Promo rules (add before checkout at discount)
    for rule in rules_config.get("promo_rules") or []:
        if _match_promo_rule(rule, intent_type, bundle_item_count):
            promo = {
                "product_ids": rule.get("product_ids") or [],
                "category_queries": rule.get("category_queries") or [],
                "discount_pct": rule.get("discount_pct", 0),
                "discount_type": rule.get("discount_type", "percent"),
                "promo_message": rule.get("promo_message", ""),
                "max_discount_per_order_cents": rule.get("max_discount_per_order_cents"),
            }
            if promo["product_ids"] or promo["category_queries"]:
                out["promo_products"].append(promo)

    return out


def _match_upsell_rule(
    rule: Dict[str, Any],
    intent_type: str,
    experience_name: str,
    purchase_intent: str,
    search_queries: List[str],
    search_query: str,
) -> bool:
    cond = rule.get("conditions") or {}
    intent_types = cond.get("intent_types") or []
    if intent_types and intent_type not in intent_types:
        return False
    occasion_kw = cond.get("occasion_contains") or []
    if occasion_kw:
        context = f"{experience_name} {' '.join(search_queries)} {search_query}".lower()
        if not any(kw in context for kw in occasion_kw):
            return False
    min_intent = cond.get("purchase_intent_min")
    if min_intent:
        order = ["exploring", "considering", "ready_to_buy"]
        try:
            if order.index(purchase_intent) < order.index(min_intent):
                return False
        except (ValueError, KeyError):
            pass
    return True


def _match_surge_rule(
    rule: Dict[str, Any],
    intent_type: str,
    purchase_intent: str,
    urgency_signals: List[str],
) -> bool:
    cond = rule.get("conditions") or {}
    intent_types = cond.get("intent_types") or []
    if intent_types and intent_type not in intent_types:
        return False
    min_intent = cond.get("purchase_intent_min")
    if min_intent:
        order = ["exploring", "considering", "ready_to_buy"]
        try:
            if order.index(purchase_intent) < order.index(min_intent):
                return False
        except (ValueError, KeyError):
            pass
    sigs = cond.get("urgency_signals") or []
    if sigs and not any(s in urgency_signals for s in sigs):
        return False
    return True


def _match_promo_rule(
    rule: Dict[str, Any],
    intent_type: str,
    bundle_item_count: int,
) -> bool:
    cond = rule.get("conditions") or {}
    if cond.get("trigger") != "before_checkout":
        return False
    min_items = cond.get("min_bundle_items", 0)
    if bundle_item_count < min_items:
        return False
    intent_types = cond.get("intent_types") or []
    if intent_types and intent_type not in intent_types:
        return False
    return True
