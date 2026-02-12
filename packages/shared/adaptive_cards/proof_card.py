"""Proof Adaptive Card - virtual proofing preview with approval buttons."""

from typing import Any, Dict, List, Optional

from .base import create_card, image, text_block


def generate_proof_approval_card_for_support_hub(
    proof: Dict[str, Any],
    *,
    preview_url: Optional[str] = None,
    proofing_service_base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Proof card with Approve/Reject for Support Hub chat.
    Actions use Action.Submit with action + proof_id; client posts to proofing API.
    If proofing_service_base_url provided, adds approve/reject URLs in metadata for client.
    """
    card = generate_proof_card(proof, preview_url=preview_url, approval_required=True)
    if proofing_service_base_url and proof.get("id"):
        pid = str(proof["id"])
        card["metadata"] = {
            "approve_url": f"{proofing_service_base_url.rstrip('/')}/api/v1/proofs/{pid}/approve",
            "reject_url": f"{proofing_service_base_url.rstrip('/')}/api/v1/proofs/{pid}/reject",
        }
    return card


def generate_proof_card(
    proof: Dict[str, Any],
    *,
    preview_url: Optional[str] = None,
    approval_required: bool = True,
) -> Dict[str, Any]:
    """
    Generate Adaptive Card for virtual proofing preview.
    Includes approval/reject buttons for user sign-off.
    """
    body = [
        text_block("Virtual Proof Preview", size="Large", weight="Bolder"),
        text_block(proof.get("description", "Please review and approve."), size="Small"),
    ]

    # Preview image or placeholder
    img_url = preview_url or proof.get("preview_url") or proof.get("image_url")
    if img_url:
        body.append(image(img_url, size="Large"))
    else:
        body.append(
            text_block("Preview will be available once proof is generated.", size="Small", is_subtle=True)
        )

    # Proof details
    details = []
    if proof.get("item_name"):
        details.append({"title": "Item", "value": proof["item_name"]})
    if proof.get("customization_summary"):
        details.append({"title": "Customization", "value": proof["customization_summary"]})
    if proof.get("revision"):
        details.append({"title": "Revision", "value": str(proof["revision"])})
    if details:
        body.append({"type": "FactSet", "facts": details})

    actions = []
    if approval_required:
        actions = [
            {"type": "Action.Submit", "title": "Approve", "data": {"action": "approve_proof", "proof_id": str(proof.get("id", ""))}},
            {"type": "Action.Submit", "title": "Request Changes", "data": {"action": "reject_proof", "proof_id": str(proof.get("id", ""))}},
        ]

    return create_card(body=body, actions=actions)
