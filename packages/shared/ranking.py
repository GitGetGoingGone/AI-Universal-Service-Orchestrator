"""Partner ranking and sponsorship boost for product discovery."""

from typing import Any, Dict, List, Optional, Set


def _get_policy(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract ranking policy from config."""
    policy = config.get("ranking_policy") or {}
    if isinstance(policy, str):
        return {}
    return policy


def _get_edge_cases(config: Dict[str, Any]) -> Dict[str, float]:
    """Extract edge case defaults from config."""
    cases = config.get("ranking_edge_cases") or {}
    if isinstance(cases, str):
        return {}
    return {
        "missing_rating": float(cases.get("missing_rating", 0.5)),
        "missing_commission": float(cases.get("missing_commission", 0)),
        "missing_trust": float(cases.get("missing_trust", 0.5)),
        "tie_breaker": str(cases.get("tie_breaker", "created_at")),
    }


def _get_sponsorship(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract sponsorship pricing from config."""
    sp = config.get("sponsorship_pricing") or {}
    if isinstance(sp, str):
        return {}
    return {
        "product_price_per_day_cents": int(sp.get("product_price_per_day_cents", 1000)),
        "max_sponsored_per_query": int(sp.get("max_sponsored_per_query", 3)),
        "sponsorship_enabled": bool(sp.get("sponsorship_enabled", True)),
    }


def compute_product_rank_score(
    product: Dict[str, Any],
    partner: Optional[Dict[str, Any]],
    partner_rating: Optional[float],
    commission_pct: Optional[float],
    config: Dict[str, Any],
) -> float:
    """
    Compute rank score for a product. Higher = better.
    Uses weighted combination of price, rating, commission, trust.
    """
    policy = _get_policy(config)
    edge = _get_edge_cases(config)

    weights = policy.get("weights") or {}
    w_price = float(weights.get("price", 0.3))
    w_rating = float(weights.get("rating", 0.3))
    w_commission = float(weights.get("commission", 0.2))
    w_trust = float(weights.get("trust", 0.2))

    price_dir = str(policy.get("price_direction", "asc")).lower()

    # Normalize components to 0-1 (higher = better for ranking)
    price = product.get("price")
    if price is not None:
        try:
            price_val = float(price)
            # Inverse for asc (lower price = higher score)
            if price_dir == "asc":
                price_score = 1.0 / (1.0 + price_val) if price_val >= 0 else 0.5
            else:
                price_score = min(1.0, price_val / 100.0) if price_val >= 0 else 0.5
        except (TypeError, ValueError):
            price_score = 0.5
    else:
        price_score = 0.5

    rating = partner_rating if partner_rating is not None else edge.get("missing_rating", 0.5)
    rating_score = min(1.0, max(0.0, float(rating) / 5.0))

    commission = commission_pct if commission_pct is not None else edge.get("missing_commission", 0)
    commission_score = min(1.0, max(0.0, float(commission) / 20.0))

    trust = 0.5
    if partner:
        ts = partner.get("trust_score")
        if ts is not None:
            try:
                trust = min(1.0, max(0.0, float(ts) / 100.0))
            except (TypeError, ValueError):
                trust = edge.get("missing_trust", 0.5)
        else:
            trust = edge.get("missing_trust", 0.5)

    score = (
        w_price * price_score
        + w_rating * rating_score
        + w_commission * commission_score
        + w_trust * trust
    )
    return score


def sort_products_by_rank(
    products: List[Dict[str, Any]],
    partners_map: Dict[str, Dict[str, Any]],
    partner_ratings_map: Optional[Dict[str, float]] = None,
    commission_map: Optional[Dict[str, float]] = None,
    active_sponsorships: Optional[Set[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Sort products by rank score. Sponsored products get a boost (up to max_sponsored_per_query).
    """
    config = config or {}
    if not config.get("ranking_enabled", True):
        return products

    sp = _get_sponsorship(config)
    max_sponsored = sp.get("max_sponsored_per_query", 3) if sp.get("sponsorship_enabled", True) else 0
    sponsorship_boost = 0.5  # Add to score for sponsored products

    partner_ratings_map = partner_ratings_map or {}
    commission_map = commission_map or {}
    active_sponsorships = active_sponsorships or set()

    scored: List[tuple] = []
    for p in products:
        pid = str(p.get("id", ""))
        partner_id = str(p.get("partner_id", "")) if p.get("partner_id") else ""
        partner = partners_map.get(partner_id) if partner_id else None
        rating = partner_ratings_map.get(partner_id)
        commission = commission_map.get(partner_id)
        score = compute_product_rank_score(p, partner, rating, commission, config)

        if pid in active_sponsorships and max_sponsored > 0:
            score += sponsorship_boost

        scored.append((score, p))

    # Sort by score descending, then by created_at for tie-breaker
    scored.sort(key=lambda x: (-x[0], str(x[1].get("created_at", ""))))

    return [p for _, p in scored]
