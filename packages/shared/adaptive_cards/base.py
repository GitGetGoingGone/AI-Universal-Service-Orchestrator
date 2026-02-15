"""Base utilities for Adaptive Card generation."""

import re
from typing import Any, Dict, List, Optional


def strip_html(text: str) -> str:
    """Remove HTML tags from text for plain display in Adaptive Cards."""
    if not text or not isinstance(text, str):
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


CARD_SCHEMA = "http://adaptivecards.io/schemas/adaptive-card.json"
CARD_VERSION = "1.5"


def create_card(
    body: List[Dict[str, Any]],
    actions: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create an Adaptive Card with standard schema and version."""
    card: Dict[str, Any] = {
        "type": "AdaptiveCard",
        "$schema": CARD_SCHEMA,
        "version": CARD_VERSION,
        "body": body,
    }
    if actions:
        card["actions"] = actions
    card.update(kwargs)
    return card


def action_submit(title: str, data: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """Create an Action.Submit button."""
    return {
        "type": "Action.Submit",
        "title": title,
        "data": data,
        **kwargs,
    }


def action_open_url(title: str, url: str, **kwargs: Any) -> Dict[str, Any]:
    """Create an Action.OpenUrl button."""
    return {
        "type": "Action.OpenUrl",
        "title": title,
        "url": url,
        **kwargs,
    }


def text_block(
    text: str,
    *,
    size: Optional[str] = None,
    weight: Optional[str] = None,
    color: Optional[str] = None,
    wrap: bool = True,
    is_subtle: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a TextBlock element."""
    elem: Dict[str, Any] = {"type": "TextBlock", "text": text, "wrap": wrap}
    if size:
        elem["size"] = size
    if weight:
        elem["weight"] = weight
    if color:
        elem["color"] = color
    if is_subtle:
        elem["isSubtle"] = True
    elem.update(kwargs)
    return elem


def fact_set(facts: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
    """Create a FactSet element."""
    return {"type": "FactSet", "facts": facts, **kwargs}


def action_set(actions: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    """Create an ActionSet element (displays action buttons). Container does not support actions; use ActionSet."""
    return {"type": "ActionSet", "actions": actions, **kwargs}


def container(
    items: List[Dict[str, Any]],
    style: Optional[str] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a Container element. If actions provided, appends an ActionSet (Container doesn't support actions)."""
    elem_items = list(items)
    if actions:
        elem_items.append(action_set(actions))
    elem: Dict[str, Any] = {"type": "Container", "items": elem_items}
    if style:
        elem["style"] = style
    elem.update(kwargs)
    return elem


def image(url: str, size: str = "Medium", **kwargs: Any) -> Dict[str, Any]:
    """Create an Image element."""
    return {"type": "Image", "url": url, "size": size, **kwargs}


def _filter_empty(items: List[Any]) -> List[Any]:
    """Remove empty dicts from a list."""
    return [i for i in items if i]
