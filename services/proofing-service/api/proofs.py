"""Virtual Proofing Engine API (Module 8)."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config import settings
from db import (
    create_proof_state,
    get_proof_state,
    list_proof_states,
    set_proof_ready,
    set_in_progress,
    approve_proof,
    reject_proof,
)

router = APIRouter(prefix="/api/v1", tags=["Proofing"])


class CreateProofBody(BaseModel):
    order_id: str
    order_leg_id: Optional[str] = None
    proof_type: str = "virtual_preview"
    prompt: Optional[str] = None


class GenerateBody(BaseModel):
    prompt: str


class ApproveBody(BaseModel):
    approved_by: Optional[str] = None
    method: str = "human"
    confidence: Optional[float] = None


class RejectBody(BaseModel):
    rejection_reason: Optional[str] = None
    rejected_by: Optional[str] = None


@router.post("/proofs")
def create_proof(body: CreateProofBody) -> Dict[str, Any]:
    """Create a proof state (pending)."""
    proof = create_proof_state(
        order_id=body.order_id,
        order_leg_id=body.order_leg_id,
        proof_type=body.proof_type,
        prompt=body.prompt,
    )
    if not proof:
        raise HTTPException(status_code=500, detail="Failed to create proof")
    return proof


@router.get("/proofs")
def list_proofs(
    order_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """List proof states."""
    data = list_proof_states(order_id=order_id, status=status)
    return {"proofs": data, "count": len(data)}


@router.get("/proofs/{proof_id}")
def get_proof(proof_id: str) -> Dict[str, Any]:
    """Get a single proof state."""
    proof = get_proof_state(proof_id)
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")
    return proof


@router.post("/proofs/{proof_id}/generate")
def generate_preview(proof_id: str, body: GenerateBody) -> Dict[str, Any]:
    """
    Generate DALL-E 3 preview for proof. Sets proof_ready with image URL.
    Requires OPENAI_API_KEY or Azure OpenAI config.
    """
    proof = get_proof_state(proof_id)
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")
    if proof.get("current_state") not in ("pending", "in_progress"):
        raise HTTPException(status_code=400, detail=f"Proof in state {proof.get('current_state')} cannot be generated")

    set_in_progress(proof_id)
    image_url = None

    if settings.dalle_configured:
        try:
            if settings.azure_openai_endpoint and settings.azure_openai_api_key:
                try:
                    from openai import AzureOpenAI
                except ImportError:
                    raise HTTPException(status_code=503, detail="openai package required for DALL-E; pip install openai")

                client = AzureOpenAI(
                    api_key=settings.azure_openai_api_key,
                    api_version="2024-02-15-preview",
                    azure_endpoint=settings.azure_openai_endpoint,
                )
                resp = client.images.generate(
                    model=settings.azure_openai_deployment,
                    prompt=body.prompt[:4000],
                    n=1,
                    size="1024x1024",
                )
            else:
                try:
                    from openai import OpenAI
                except ImportError:
                    raise HTTPException(status_code=503, detail="openai package required for DALL-E; pip install openai")

                client = OpenAI(api_key=settings.openai_api_key)
                resp = client.images.generate(
                    model="dall-e-3",
                    prompt=body.prompt[:4000],
                    n=1,
                    size="1024x1024",
                )
            if resp.data and len(resp.data) > 0:
                image_url = resp.data[0].url or (getattr(resp.data[0], "b64_json", None) and f"data:image/png;base64,{resp.data[0].b64_json}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DALL-E generation failed: {str(e)}")

    if not image_url:
        image_url = "https://placehold.co/1024x1024?text=No+DALL-E+config"
        if not settings.dalle_configured:
            pass

    proof = set_proof_ready(proof_id, image_url)
    if not proof:
        raise HTTPException(status_code=500, detail="Failed to set proof ready")
    return proof


@router.post("/proofs/{proof_id}/approve")
def approve_proof_endpoint(proof_id: str, body: ApproveBody) -> Dict[str, Any]:
    """Approve a proof (proof_ready -> approved)."""
    proof = approve_proof(
        proof_id,
        approved_by=body.approved_by,
        method=body.method,
        confidence=body.confidence,
    )
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found or not in proof_ready state")
    return proof


@router.post("/proofs/{proof_id}/reject")
def reject_proof_endpoint(proof_id: str, body: RejectBody) -> Dict[str, Any]:
    """Reject a proof (proof_ready -> rejected)."""
    proof = reject_proof(
        proof_id,
        rejection_reason=body.rejection_reason,
        rejected_by=body.rejected_by,
    )
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found or not in proof_ready state")
    return proof


class VisionCheckBody(BaseModel):
    source_of_truth_url: Optional[str] = None


@router.post("/proofs/{proof_id}/vision-check")
def vision_check(proof_id: str, body: Optional[VisionCheckBody] = None) -> Dict[str, Any]:
    """
    Vision AI comparison: proof image vs source of truth.
    Returns similarity score and recommendation (auto_approve, human_review, reject).
    If auto_approve, optionally auto-approves the proof.
    """
    from vision_ai import auto_approve_with_vision_ai

    proof = get_proof_state(proof_id)
    if not proof:
        raise HTTPException(status_code=404, detail="Proof not found")
    if proof.get("current_state") != "proof_ready":
        raise HTTPException(status_code=400, detail=f"Proof must be in proof_ready state, got {proof.get('current_state')}")

    img_url = proof.get("proof_image_url")
    if not img_url:
        return {"similarity_score": 0.0, "recommendation": "reject", "message": "No proof image"}

    source_url = (body and body.source_of_truth_url) or None
    score, recommendation = auto_approve_with_vision_ai(img_url, source_url)

    result = {"similarity_score": score, "recommendation": recommendation}
    if recommendation == "auto_approve":
        approved = approve_proof(proof_id, method="vision_ai", confidence=score)
        if approved:
            result["auto_approved"] = True
            result["proof"] = approved

    return result
