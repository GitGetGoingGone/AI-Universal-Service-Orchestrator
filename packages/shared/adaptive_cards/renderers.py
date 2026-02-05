"""Platform-specific Adaptive Card renderers (Gemini, ChatGPT, WhatsApp)."""

from typing import Any, Dict, Literal, Optional

Platform = Literal["gemini", "chatgpt", "whatsapp"]


def render_for_platform(
    card: Dict[str, Any],
    platform: Platform,
    *,
    fallback_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Adapt an Adaptive Card for platform-specific rendering.

    - Gemini: Dynamic View - pass through as-is (native Adaptive Cards)
    - ChatGPT: Native rendering - ensure action data is compatible
    - WhatsApp: Fallback to interactive buttons (list of actions as buttons)
    """
    if platform == "gemini":
        return _for_gemini(card)
    if platform == "chatgpt":
        return _for_chatgpt(card)
    if platform == "whatsapp":
        return _for_whatsapp(card, fallback_text=fallback_text)
    raise ValueError(f"Unknown platform: {platform}")


def _for_gemini(card: Dict[str, Any]) -> Dict[str, Any]:
    """Gemini Dynamic View - use Adaptive Card as-is."""
    return card


def _for_chatgpt(card: Dict[str, Any]) -> Dict[str, Any]:
    """ChatGPT - ensure compatibility with Instant Checkout and native rendering."""
    # ChatGPT supports Adaptive Cards 1.5; ensure required fields
    result = dict(card)
    if "version" not in result:
        result["version"] = "1.5"
    if "type" not in result:
        result["type"] = "AdaptiveCard"
    return result


def _for_whatsapp(card: Dict[str, Any], fallback_text: Optional[str] = None) -> Dict[str, Any]:
    """
    WhatsApp - extract interactive button payload.
    WhatsApp doesn't render Adaptive Cards; use interactive list/button message.
    Returns a structure suitable for Twilio WhatsApp API or similar.
    """
    body_texts = []
    for elem in card.get("body", []):
        if elem.get("type") == "TextBlock":
            body_texts.append(elem.get("text", ""))
    text = fallback_text or "\n".join(body_texts) or "Please choose an option."

    # Extract actions as buttons (max 3 for WhatsApp quick reply)
    buttons = []
    for action in card.get("actions", [])[:3]:
        if action.get("type") == "Action.Submit":
            buttons.append(
                {
                    "type": "reply",
                    "reply": {"id": _serialize_action_data(action.get("data", {})), "title": action.get("title", "Option")[:20]},
                }
            )
        elif action.get("type") == "Action.OpenUrl":
            buttons.append(
                {
                    "type": "url",
                    "url": action.get("url", ""),
                    "text": action.get("title", "Open")[:20],
                }
            )

    return {
        "platform": "whatsapp",
        "text": text,
        "buttons": buttons,
        "adaptive_card": card,  # Keep original for reference
    }


def _serialize_action_data(data: Dict[str, Any]) -> str:
    """Serialize action data for WhatsApp button ID (max 256 chars)."""
    parts = [f"{k}={v}" for k, v in data.items()]
    s = "|".join(parts)
    return s[:256] if len(s) > 256 else s
