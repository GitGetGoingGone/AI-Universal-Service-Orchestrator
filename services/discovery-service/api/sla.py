"""SLA Re-Sourcing Job API - find legs where SLA exceeded, notify user, store alternatives."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from db import (
    get_supabase,
    search_products,
    create_sla_re_sourcing_pending,
    get_partners_available_to_customize,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["SLA"])


@router.get("/sla/pending")
async def get_sla_pending(thread_id: str) -> Dict[str, Any]:
    """Get pending SLA re-sourcing for thread (awaiting user response)."""
    from db import get_sla_re_sourcing_pending_by_thread
    from fastapi import HTTPException
    pending = await get_sla_re_sourcing_pending_by_thread(thread_id)
    if not pending:
        raise HTTPException(status_code=404, detail="No pending SLA re-sourcing")
    leg_id = pending.get("experience_session_leg_id")
    if not leg_id:
        raise HTTPException(status_code=404, detail="No pending SLA re-sourcing")
    return {
        "experience_session_leg_id": str(leg_id),
        "alternatives_snapshot": pending.get("alternatives_snapshot") or [],
    }


@router.post("/sla/run-job")
async def run_sla_job() -> Dict[str, Any]:
    """
    SLA job: find legs where partner hasn't started design within sla_response_hours.
    For each: find similar alternatives, create sla_re_sourcing_pending, return list for notification.
    Call from cron (e.g. every 15 min).
    """
    client = get_supabase()
    if not client:
        raise HTTPException(status_code=503, detail="Database not configured")

    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        legs = (
            client.table("experience_session_legs")
            .select("id, experience_session_id, partner_id, product_id, status, re_sourcing_state, created_at")
            .in_("status", ["ready", "in_customization"])
            .is_("design_started_at", "null")
            .neq("re_sourcing_state", "awaiting_user_response")
            .execute()
        )
        notified = []
        for leg in legs.data or []:
            if leg.get("re_sourcing_state") == "awaiting_user_response":
                continue
            session = (
                client.table("experience_sessions")
                .select("thread_id, order_id")
                .eq("id", leg.get("experience_session_id"))
                .single()
                .execute()
            )
            if not session.data or not session.data.get("thread_id"):
                continue
            order_id = session.data.get("order_id")
            if not order_id:
                continue
            order = (
                client.table("orders")
                .select("paid_at")
                .eq("id", order_id)
                .single()
                .execute()
            )
            if not order.data or not order.data.get("paid_at"):
                continue
            paid_at = order.data.get("paid_at")
            partner_id = str(leg.get("partner_id", ""))
            scp = (
                client.table("shopify_curated_partners")
                .select("internal_agent_registry_id")
                .eq("partner_id", partner_id)
                .limit(1)
                .execute()
            )
            if not scp.data:
                continue
            reg_id = scp.data[0].get("internal_agent_registry_id")
            if not reg_id:
                continue
            reg = (
                client.table("internal_agent_registry")
                .select("sla_response_hours, available_to_customize")
                .eq("id", reg_id)
                .single()
                .execute()
            )
            if not reg.data or not reg.data.get("available_to_customize"):
                continue
            hours = float(reg.data.get("sla_response_hours") or 24)
            from datetime import datetime as dt
            try:
                paid_dt = dt.fromisoformat(paid_at.replace("Z", "+00:00"))
            except Exception:
                continue
            if (datetime.now(timezone.utc) - paid_dt).total_seconds() < hours * 3600:
                continue

            product = (
                client.table("products")
                .select("name, capabilities")
                .eq("id", leg.get("product_id"))
                .single()
                .execute()
            )
            query = product.data.get("name", "product") if product.data else "product"
            caps = product.data.get("capabilities") or [] if product.data else []
            if isinstance(caps, list) and caps:
                query = caps[0]

            alternatives = await search_products(
                query=query,
                limit=5,
                exclude_partner_id=partner_id,
            )
            if not alternatives:
                continue

            alt_snapshot = [
                {"id": str(a.get("id")), "name": a.get("name"), "price": float(a.get("price", 0)), "partner_id": str(a.get("partner_id", ""))}
                for a in alternatives[:3]
            ]
            pid = await create_sla_re_sourcing_pending(leg["id"], alt_snapshot)
            if pid:
                notified.append({
                    "thread_id": session.data["thread_id"],
                    "leg_id": leg["id"],
                    "alternatives": alt_snapshot,
                })

        return {"notified": notified, "count": len(notified)}
    except Exception as e:
        logger.exception("SLA job failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
