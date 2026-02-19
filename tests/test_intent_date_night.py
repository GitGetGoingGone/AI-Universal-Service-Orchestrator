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


def test_you_suggest_uses_date_night_not_birthday():
    """When user says 'you suggest' after date night probing, use date night categories, not 'birthday gifts' from earlier."""
    from llm import _heuristic_resolve

    last_suggestion = "I'd love to help you plan a perfect date night! To tailor the experience, could you tell me: 1) What date? 2) Budget? 3) Dietary preferences? 4) Location?"
    recent_conversation = [
        {"role": "user", "content": "best birthday gifts under $50"},
        {"role": "assistant", "content": "Here are some chocolates..."},
        {"role": "user", "content": "plan a date night"},
        {"role": "assistant", "content": last_suggestion[:150]},
        {"role": "user", "content": "you suggest"},
    ]

    result = _heuristic_resolve(
        "you suggest",
        last_suggestion=last_suggestion,
        recent_conversation=recent_conversation,
    )

    assert result["intent_type"] == "discover_composite"
    assert result.get("search_queries") == ["flowers", "dinner", "limo"]
    assert "birthday" not in str(result.get("search_queries", [])).lower()
    assert "gift" not in str(result.get("search_queries", [])).lower()


def test_topic_change_from_date_night_to_chocolates():
    """When user says 'actually I want chocolates' during date night probing, treat as fresh discover intent."""
    from llm import _heuristic_resolve

    last_suggestion = "I'd love to help you plan a perfect date night! What date? Budget? Dietary preferences? Location?"
    result = _heuristic_resolve(
        "actually I want chocolates",
        last_suggestion=last_suggestion,
        recent_conversation=[
            {"role": "user", "content": "plan a date night"},
            {"role": "assistant", "content": last_suggestion[:100]},
            {"role": "user", "content": "actually I want chocolates"},
        ],
    )

    assert result["intent_type"] == "discover"
    assert "chocolates" in (result.get("search_query") or "").lower()


def test_topic_change_forget_that_birthday_gifts():
    """When user says 'forget that, birthday gifts for my nephew' during gift probing, treat as fresh intent."""
    from llm import _heuristic_resolve

    last_suggestion = "I'd love to help find the perfect gift! Who is it for—age or relationship? Boy, girl, or neutral? Any interests?"
    result = _heuristic_resolve(
        "forget that, birthday gifts for my nephew",
        last_suggestion=last_suggestion,
    )

    assert result["intent_type"] == "discover"
    assert "birthday" in (result.get("search_query") or "") or "gift" in (result.get("search_query") or "").lower()


def test_birthday_gifts_under_50_probes():
    """'Best birthday gifts under $50' should trigger probing, not direct discover."""
    from llm import _heuristic_resolve

    result = _heuristic_resolve("best birthday gifts under $50")

    assert result["intent_type"] == "discover"
    assert result.get("recommended_next_action") == "complete_with_probing"
    assert result.get("entities")  # budget entity
