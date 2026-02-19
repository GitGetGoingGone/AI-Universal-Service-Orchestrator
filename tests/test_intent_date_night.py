"""Tests for intent resolution: date night probing flow."""

import sys
from pathlib import Path

# Add project root and intent-service to path
_root = Path(__file__).resolve().parents[1]
_intent = _root / "services" / "intent-service"
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_intent))


def test_date_night_probing_answer_uses_original_request():
    """When user answers 'anytime this week depending on weather', categories come from 'plan a date night', not the answer."""
    from llm import _heuristic_resolve

    last_suggestion = "I'd love to help you plan a perfect date night! To tailor the experience, could you tell me: 1) What date are you planning for? 2) Do you have a budget in mind? 3) Any dietary preferences? 4) Preferred location or area?"
    recent_conversation = [
        {"role": "user", "content": "Plan a date night"},
        {"role": "assistant", "content": last_suggestion[:150]},
        {"role": "user", "content": "anytime this week depending on weather"},
    ]

    result = _heuristic_resolve(
        "anytime this week depending on weather",
        last_suggestion=last_suggestion,
        recent_conversation=recent_conversation,
    )

    assert result["intent_type"] == "discover_composite"
    assert result.get("search_queries") == ["flowers", "dinner", "limo"]
    assert "anytime" not in str(result.get("search_queries", [])).lower()
    assert "weather" not in str(result.get("search_queries", [])).lower()
    assert result.get("search_query") and "None" not in str(result.get("search_query"))
    assert "date" in (result.get("experience_name") or "") and "night" in (result.get("experience_name") or "")
    opts = result.get("bundle_options", [])
    assert opts
    assert any("date night" in str(o.get("label", "")).lower() for o in opts) or opts[0].get("categories") == ["flowers", "dinner", "limo"]
