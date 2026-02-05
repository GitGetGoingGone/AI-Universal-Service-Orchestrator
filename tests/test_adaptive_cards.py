"""Tests for Adaptive Cards library."""

import pytest

from packages.shared.adaptive_cards import (
    CARD_SCHEMA,
    CARD_VERSION,
    create_card,
    generate_product_card,
    generate_bundle_card,
    generate_proof_card,
    generate_timechain_card,
    generate_progress_ledger_card,
    generate_checkout_card,
    generate_conflict_suggestion_card,
    render_for_platform,
)


class TestBase:
    def test_create_card(self):
        card = create_card(body=[{"type": "TextBlock", "text": "Hello"}])
        assert card["type"] == "AdaptiveCard"
        assert card["$schema"] == CARD_SCHEMA
        assert card["version"] == CARD_VERSION
        assert len(card["body"]) == 1

    def test_create_card_with_actions(self):
        card = create_card(
            body=[{"type": "TextBlock", "text": "Hi"}],
            actions=[{"type": "Action.Submit", "title": "OK", "data": {"action": "ok"}}],
        )
        assert "actions" in card
        assert len(card["actions"]) == 1


class TestProductCard:
    def test_empty_products(self):
        card = generate_product_card([])
        assert card["type"] == "AdaptiveCard"
        assert "No products found" in card["body"][0]["text"]

    def test_single_product(self):
        products = [
            {"id": "p1", "name": "Flowers", "price": 29.99, "currency": "USD", "capabilities": ["delivery"]},
        ]
        card = generate_product_card(products)
        assert "Found 1 product(s)" in card["body"][0]["text"]
        assert len(card["body"]) >= 2
        assert any("Add to Bundle" in str(a.get("title", "")) for a in card["body"][1].get("actions", []))

    def test_multiple_products(self):
        products = [
            {"id": "p1", "name": "A", "price": 10, "currency": "USD"},
            {"id": "p2", "name": "B", "price": 20, "currency": "USD"},
        ]
        card = generate_product_card(products)
        assert "Found 2 product(s)" in card["body"][0]["text"]


class TestBundleCard:
    def test_bundle_card(self):
        bundle = {
            "id": "b1",
            "name": "My Bundle",
            "total_price": 49.99,
            "currency": "USD",
            "item_count": 2,
            "items": [
                {"id": "i1", "name": "Item 1", "price": 25, "currency": "USD"},
                {"id": "i2", "name": "Item 2", "price": 24.99, "currency": "USD"},
            ],
        }
        card = generate_bundle_card(bundle)
        assert "My Bundle" in card["body"][0]["text"]
        assert "Proceed to Checkout" in str([a["title"] for a in card["actions"]])


class TestProofCard:
    def test_proof_card(self):
        proof = {"id": "pr1", "item_name": "Custom Shirt", "customization_summary": "Logo on chest"}
        card = generate_proof_card(proof)
        assert "Virtual Proof Preview" in card["body"][0]["text"]
        assert any(a["data"]["action"] == "approve_proof" for a in card["actions"])


class TestTimeChainCard:
    def test_timechain_card(self):
        timechain = {
            "id": "tc1",
            "total_duration": "2h",
            "leg_count": 2,
            "legs": [
                {"name": "Pickup", "eta": "10:00", "deadline": "10:30"},
                {"name": "Delivery", "eta": "11:30"},
            ],
        }
        card = generate_timechain_card(timechain)
        assert "Journey Timeline" in card["body"][0]["text"]


class TestProgressLedgerCard:
    def test_progress_ledger_card(self):
        card = generate_progress_ledger_card(
            "Still waiting to buy the flowers",
            thought="Monitoring weather",
            if_then_logic={"condition": {"weather": "sunny"}, "action": {"type": "order", "item": "flowers"}},
        )
        assert "Still waiting" in card["body"][0]["text"]
        assert any("IF" in str(e) for e in card["body"])


class TestCheckoutCard:
    def test_checkout_card(self):
        order = {
            "id": "o1",
            "subtotal": 50,
            "tax": 5,
            "total": 55,
            "currency": "USD",
            "line_items": [{"name": "Item A", "quantity": 1, "price": 50, "currency": "USD"}],
        }
        card = generate_checkout_card(order)
        assert "Order Summary" in card["body"][0]["text"]
        assert "Complete Checkout" in str([a["title"] for a in card["actions"]])


class TestConflictSuggestionCard:
    def test_conflict_card(self):
        conflict = {
            "id": "c1",
            "message": "Adding chocolates will make you 15 minutes late for dinner.",
            "delay_minutes": 15,
            "affected_leg": "Dinner Reservation",
            "suggestions": [
                {
                    "id": "s1",
                    "message": "Courier chocolates separately",
                    "action_title": "Courier Separately",
                    "alternative": {"type": "courier", "estimated_cost": 12.99},
                },
            ],
        }
        card = generate_conflict_suggestion_card(conflict)
        assert "Conflict Detected" in card["body"][0]["text"]
        assert "Proceed Anyway" in str([a["title"] for a in card["actions"]])


class TestRenderers:
    def test_render_gemini(self):
        card = create_card(body=[{"type": "TextBlock", "text": "Hi"}])
        out = render_for_platform(card, "gemini")
        assert out == card

    def test_render_chatgpt(self):
        card = create_card(body=[{"type": "TextBlock", "text": "Hi"}])
        out = render_for_platform(card, "chatgpt")
        assert out["type"] == "AdaptiveCard"
        assert "version" in out

    def test_render_whatsapp(self):
        card = create_card(
            body=[{"type": "TextBlock", "text": "Choose an option"}],
            actions=[{"type": "Action.Submit", "title": "Yes", "data": {"action": "yes"}}],
        )
        out = render_for_platform(card, "whatsapp")
        assert out["platform"] == "whatsapp"
        assert "text" in out
        assert "buttons" in out
        assert len(out["buttons"]) == 1

    def test_render_unknown_platform(self):
        card = create_card(body=[])
        with pytest.raises(ValueError, match="Unknown platform"):
            render_for_platform(card, "unknown")
