"""Schema.org JSON-LD for Intent / ResolveAction."""

from typing import Any, Dict, List, Optional


def intent_ld(
    intent_type: str,
    search_query: Optional[str] = None,
    confidence_score: Optional[float] = None,
    entities: Optional[List[Dict[str, Any]]] = None,
    intent_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Intent as Schema.org result of ResolveAction."""
    out: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Thing",
        "name": intent_type,
    }
    if search_query is not None:
        out["description"] = search_query
    if confidence_score is not None:
        out["additionalProperty"] = out.get("additionalProperty", [])
        if isinstance(out["additionalProperty"], list):
            out["additionalProperty"].append(
                {"@type": "PropertyValue", "name": "confidenceScore", "value": confidence_score}
            )
    if entities:
        out["mainEntity"] = {"@type": "ItemList", "itemListElement": entities}
    if intent_id:
        out["identifier"] = intent_id
    out.update(kwargs)
    return out


def resolve_action_ld(
    intent_type: str,
    search_query: Optional[str] = None,
    search_queries: Optional[List[str]] = None,
    experience_name: Optional[str] = None,
    confidence_score: Optional[float] = None,
    entities: Optional[List[Dict[str, Any]]] = None,
    intent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """ResolveAction with result Intent (machine_readable for intent resolution)."""
    result: Dict[str, Any] = {
        "@type": "Thing",
        "name": intent_type,
        "description": search_query,
        "identifier": intent_id,
    }
    if search_queries:
        result["searchQueries"] = search_queries
    if experience_name:
        result["experienceName"] = experience_name
    if confidence_score is not None:
        result["additionalProperty"] = [
            {"@type": "PropertyValue", "name": "confidenceScore", "value": confidence_score}
        ]
    if entities:
        result["mainEntity"] = {"@type": "ItemList", "itemListElement": entities}
    return {
        "@context": "https://schema.org",
        "@type": "ResolveAction",
        "result": result,
    }
