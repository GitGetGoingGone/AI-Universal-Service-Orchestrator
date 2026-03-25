"""Run multi-agent bundle scouts; PAO traces, todos, sentiment metrics, aggregation."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx

from config import settings

from .agent_registry import (
    AGENT_EVENTS,
    AGENT_LOCAL_DB,
    AGENT_MCP,
    AGENT_RESOURCING,
    AGENT_UCP,
    AGENT_WEATHER,
    get_resolved_registry,
)
from .agents import (
    AgentInvocation,
    AgentOperation,
    AgentResult,
    OperationProgress,
    trace_append,
)

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 25.0


def _intent_location(intent: Dict[str, Any]) -> Optional[str]:
    for e in intent.get("entities") or []:
        if isinstance(e, dict) and (e.get("type") or "").lower() == "location":
            v = (e.get("value") or "").strip()
            if v:
                return v
    return None


def _search_query(intent: Dict[str, Any], user_message: str) -> str:
    q = (intent.get("search_query") or "").strip()
    if q:
        return q[:200]
    sq = intent.get("search_queries")
    if isinstance(sq, list) and sq:
        return " ".join(str(x) for x in sq[:5] if x)[:200]
    return (user_message or "")[:200] or "browse"


async def _invoke_local_db(
    inv: AgentInvocation,
    discover_products_fn: Callable[..., Awaitable[Dict[str, Any]]],
    plan_labels: List[str],
) -> AgentResult:
    trace: List[AgentOperation] = []
    for lbl in plan_labels or ["Context check", "Discovery", "Curate matches"]:
        trace_append(trace, "PLAN", lbl)
    trace_append(trace, "ACTION", "Searching local inventory for matching products")
    try:
        r = await discover_products_fn(
            query=_search_query(inv.intent, inv.user_message),
            limit=inv.limit,
            location=inv.location,
        )
        data = r.get("data", r) if isinstance(r, dict) else {}
        products = data.get("products") or []
        count = data.get("count", len(products) if isinstance(products, list) else 0)
        trace_append(
            trace,
            "OBSERVE",
            f"Found {count} candidate products in local inventory; prioritizing relevance and availability.",
        )
        return AgentResult(
            id=AGENT_LOCAL_DB,
            label="Local inventory",
            kind="discovery",
            status="succeeded",
            summary=f"Local DB: {count} matches",
            details={"source": "local_db", "count": count, "sample_ids": [str(p.get("id")) for p in products[:5] if isinstance(p, dict)]},
            operations=[
                OperationProgress(label="Query catalog", status="done"),
                OperationProgress(label="Rank results", status="done"),
            ],
            trace=trace,
        )
    except Exception as e:
        logger.warning("local_db agent failed: %s", e)
        trace_append(trace, "OBSERVE", "Local inventory search hit an issue; continuing with other sources.")
        return AgentResult(
            id=AGENT_LOCAL_DB,
            label="Local inventory",
            kind="discovery",
            status="failed",
            summary="Local DB: unavailable",
            details={"error": str(e)},
            trace=trace,
        )


async def _invoke_ucp(inv: AgentInvocation, plan_labels: List[str]) -> AgentResult:
    trace: List[AgentOperation] = []
    for lbl in plan_labels or ["Context check", "UCP discovery", "Relevance filter"]:
        trace_append(trace, "PLAN", lbl)
    trace_append(trace, "ACTION", "Querying UCP catalog for curated gift and product options")
    q = _search_query(inv.intent, inv.user_message)
    url = f"{settings.discovery_service_url.rstrip('/')}/api/v1/ucp/items"
    try:
        from clients import _gateway_headers_for_discovery

        path = "/api/v1/ucp/items"
        headers = _gateway_headers_for_discovery("GET", path)
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as http:
            r = await http.get(url, params={"query": q, "limit": min(inv.limit, 30)}, headers=headers)
            r.raise_for_status()
            body = r.json()
        inner = body.get("data", body)
        items = inner.get("items") if isinstance(inner, dict) else None
        if items is None and isinstance(inner, list):
            items = inner
        n = len(items) if isinstance(items, list) else 0
        trace_append(trace, "OBSERVE", f"UCP returned {n} items aligned to your request.")
        return AgentResult(
            id=AGENT_UCP,
            label="UCP catalog",
            kind="discovery",
            status="succeeded",
            summary=f"UCP: {n} items",
            details={"source": "ucp", "count": n},
            operations=[OperationProgress(label="UCP search", status="done")],
            trace=trace,
        )
    except Exception as e:
        logger.debug("ucp agent: %s", e)
        trace_append(trace, "OBSERVE", "UCP feed did not return results this time; local inventory still applies.")
        return AgentResult(
            id=AGENT_UCP,
            label="UCP catalog",
            kind="discovery",
            status="failed",
            summary="UCP: no feed",
            details={"error": str(e)},
            trace=trace,
        )


async def _invoke_mcp(inv: AgentInvocation, plan_labels: List[str]) -> AgentResult:
    trace: List[AgentOperation] = []
    for lbl in plan_labels or ["Mesh readiness", "Partner catalog scan", "Offer alignment"]:
        trace_append(trace, "PLAN", lbl)
    trace_append(trace, "ACTION", "Checking curated Shopify MCP partners for extra assortment")
    try:
        from db import get_supabase

        n_shopify = 0
        client = get_supabase()
        if client:
            r = (
                client.table("internal_agent_registry")
                .select("id")
                .eq("enabled", True)
                .eq("transport_type", "SHOPIFY")
                .execute()
            )
            n_shopify = len(r.data or [])
        trace_append(
            trace,
            "OBSERVE",
            f"MCP mesh: {n_shopify} curated partner channel(s) available; bundle legs can pull from mesh when enabled.",
        )
        return AgentResult(
            id=AGENT_MCP,
            label="MCP / Shopify mesh",
            kind="integration",
            status="succeeded",
            summary=f"MCP: {n_shopify} partner channel(s) ready",
            details={"shopify_agents": n_shopify},
            trace=trace,
        )
    except Exception as e:
        trace_append(trace, "OBSERVE", "MCP mesh is not fully configured; skipping mesh-only SKUs for this turn.")
        return AgentResult(
            id=AGENT_MCP,
            label="MCP / Shopify mesh",
            kind="integration",
            status="failed",
            summary="MCP: not configured",
            details={"error": str(e)},
            trace=trace,
        )


async def _invoke_weather(inv: AgentInvocation, plan_labels: List[str]) -> AgentResult:
    trace: List[AgentOperation] = []
    for lbl in plan_labels or ["Location context", "Conditions lookup", "Comfort readout"]:
        trace_append(trace, "PLAN", lbl)
    loc = inv.location or "your area"
    trace_append(trace, "ACTION", f"Checking current weather for {loc}")
    try:
        from agentic import loop as ag_loop

        raw = await ag_loop._get_weather(loc)  # noqa: SLF001
        if raw.get("error"):
            trace_append(trace, "OBSERVE", "Weather service is not configured or location could not be resolved.")
            return AgentResult(
                id=AGENT_WEATHER,
                label="Weather context",
                kind="context",
                status="failed",
                summary="Weather: unavailable",
                details={"error": raw.get("error")},
                user_cancellable=True,
                user_editable=True,
                trace=trace,
            )
        d = raw.get("data") or {}
        temp = d.get("temp")
        desc = d.get("description") or ""
        min_f = inv.skills.get("min_temp_f")
        if min_f is not None and temp is not None:
            try:
                if float(temp) < float(min_f):
                    trace_append(
                        trace,
                        "OBSERVE",
                        f"Temperature is below your preference ({min_f}°F); suggesting indoor-friendly options where relevant.",
                    )
                else:
                    trace_append(trace, "OBSERVE", f"Conditions look comfortable for outdoor plans ({temp}°F, {desc}).")
            except (TypeError, ValueError):
                trace_append(trace, "OBSERVE", f"Current conditions: {temp}°F — {desc}".strip())
        else:
            trace_append(trace, "OBSERVE", f"Current conditions: {temp}°F — {desc}".strip() if temp else str(desc))
        return AgentResult(
            id=AGENT_WEATHER,
            label="Weather context",
            kind="context",
            status="succeeded",
            summary=f"Weather: {temp}°F" if temp is not None else "Weather: updated",
            details=d,
            user_cancellable=True,
            user_editable=True,
            trace=trace,
        )
    except Exception as e:
        trace_append(trace, "OBSERVE", "Could not read weather; continuing without a weather pivot.")
        return AgentResult(
            id=AGENT_WEATHER,
            label="Weather context",
            kind="context",
            status="failed",
            summary="Weather: error",
            details={"error": str(e)},
            user_cancellable=True,
            user_editable=True,
            trace=trace,
        )


async def _invoke_events(inv: AgentInvocation, plan_labels: List[str]) -> AgentResult:
    trace: List[AgentOperation] = []
    for lbl in plan_labels or ["Venue context", "Event discovery", "Highlights"]:
        trace_append(trace, "PLAN", lbl)
    loc = inv.location or "near you"
    trace_append(trace, "ACTION", f"Looking up upcoming occasions near {loc}")
    try:
        from agentic import loop as ag_loop

        raw = await ag_loop._get_upcoming_occasions(loc, limit=5)  # noqa: SLF001
        if raw.get("error"):
            trace_append(trace, "OBSERVE", "Events API not configured; no local occasion list for this turn.")
            return AgentResult(
                id=AGENT_EVENTS,
                label="Local events",
                kind="context",
                status="failed",
                summary="Events: unavailable",
                details={"error": raw.get("error")},
                user_cancellable=True,
                user_editable=True,
                trace=trace,
            )
        events = (raw.get("data") or {}).get("events") or []
        trace_append(trace, "OBSERVE", f"Surfaced {len(events)} upcoming happenings you may want to weave into the plan.")
        return AgentResult(
            id=AGENT_EVENTS,
            label="Local events",
            kind="context",
            status="succeeded",
            summary=f"Events: {len(events)} found",
            details={"events": events},
            user_cancellable=True,
            user_editable=True,
            trace=trace,
        )
    except Exception as e:
        trace_append(trace, "OBSERVE", "Events lookup failed softly; core bundle discovery still applies.")
        return AgentResult(
            id=AGENT_EVENTS,
            label="Local events",
            kind="context",
            status="failed",
            summary="Events: error",
            details={"error": str(e)},
            user_cancellable=True,
            user_editable=True,
            trace=trace,
        )


async def _invoke_resourcing(inv: AgentInvocation, plan_labels: List[str]) -> AgentResult:
    trace: List[AgentOperation] = []
    for lbl in plan_labels or ["Thread health", "Alternative inventory", "Recovery narrative"]:
        trace_append(trace, "PLAN", lbl)
    trace_append(trace, "ACTION", "Checking SLA re-sourcing queue for this conversation")
    try:
        from clients import get_sla_re_sourcing_pending

        if not inv.thread_id:
            trace_append(trace, "OBSERVE", "No thread context; re-sourcing monitors idle.")
            return AgentResult(
                id=AGENT_RESOURCING,
                label="Re-sourcing",
                kind="resourcing",
                status="succeeded",
                summary="Re-sourcing: idle",
                details={},
                user_cancellable=True,
                trace=trace,
            )
        pending = await get_sla_re_sourcing_pending(inv.thread_id)
        if pending:
            alts = pending.get("alternatives_snapshot") or []
            trace_append(
                trace,
                "OBSERVE",
                f"Primary partner may need a swap; {len(alts)} alternative option(s) are on standby for your confirmation.",
            )
            return AgentResult(
                id=AGENT_RESOURCING,
                label="Re-sourcing",
                kind="resourcing",
                status="succeeded",
                summary=f"Re-sourcing: {len(alts)} alternative(s) ready",
                details={"pending": True, "alternatives_count": len(alts)},
                user_cancellable=True,
                trace=trace,
            )
        trace_append(trace, "OBSERVE", "No active re-sourcing requests; vendors look stable for this thread.")
        return AgentResult(
            id=AGENT_RESOURCING,
            label="Re-sourcing",
            kind="resourcing",
            status="succeeded",
            summary="Re-sourcing: clear",
            details={"pending": False},
            user_cancellable=True,
            trace=trace,
        )
    except Exception as e:
        trace_append(trace, "OBSERVE", "Re-sourcing check completed with warnings; support can still intervene manually.")
        return AgentResult(
            id=AGENT_RESOURCING,
            label="Re-sourcing",
            kind="resourcing",
            status="failed",
            summary="Re-sourcing: check failed",
            details={"error": str(e)},
            user_cancellable=True,
            trace=trace,
        )


def _effective_skills(agent_def: Dict[str, Any], overrides: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    base = agent_def.get("skills") if isinstance(agent_def.get("skills"), dict) else {}
    skills = dict(base)
    if agent_def.get("user_editable") and isinstance(overrides.get(agent_id), dict):
        skills.update(overrides[agent_id])
    return skills


async def run_multi_agent_bundle(
    *,
    intent_data: Dict[str, Any],
    user_message: str,
    thread_id: Optional[str],
    user_id: Optional[str],
    limit: int,
    discover_products_fn: Callable[..., Awaitable[Dict[str, Any]]],
    agents_requested: Optional[List[str]],
    cancel_agent_ids: Optional[List[str]],
    agent_skills_overrides: Optional[Dict[str, Any]],
    message_count: int = 0,
) -> Dict[str, Any]:
    """
    Returns multi_agent_status, todos, thought_timelines, memory_health, credit_usage, narrative, merged_hints.
    """
    t0 = time.perf_counter()
    reg = get_resolved_registry()
    if not reg.get("enabled"):
        return {}

    cancel_set = {str(x) for x in (cancel_agent_ids or []) if x}
    overrides = agent_skills_overrides if isinstance(agent_skills_overrides, dict) else {}
    agents_by_id = {a["id"]: a for a in reg["agents"]}

    workflow_order: List[str] = [str(x) for x in reg.get("workflow_order") or []]
    req = [str(x) for x in agents_requested] if agents_requested else []
    # Default: all enabled-default agents that are enabled in config
    if not req:
        req = [a["id"] for a in reg["agents"] if a.get("enabled", True) and a.get("enabled_default", True)]
    else:
        req = [x for x in req if x in agents_by_id and agents_by_id[x].get("enabled", True)]

    ordered = [aid for aid in workflow_order if aid in req]
    for aid in req:
        if aid not in ordered:
            ordered.append(aid)

    location = _intent_location(intent_data)

    async def run_one(aid: str) -> AgentResult:
        adef = agents_by_id.get(aid)
        if not adef or not adef.get("enabled", True):
            return AgentResult(
                id=aid,
                label=aid,
                status="cancelled",
                summary="Agent disabled by platform admin",
                trace=[AgentOperation(phase="OBSERVE", label="Skipped — disabled in admin config", timestamp=time.time())],
            )
        if aid in cancel_set and adef.get("user_cancellable"):
            return AgentResult(
                id=aid,
                label=str(adef.get("display_name") or aid),
                kind=adef.get("kind") or "discovery",  # type: ignore[arg-type]
                status="cancelled",
                summary="Skipped (cancelled by you)",
                user_cancellable=True,
                user_editable=bool(adef.get("user_editable")),
                trace=[AgentOperation(phase="PLAN", label="User skipped this scout for the run", timestamp=time.time())],
            )
        skills = _effective_skills(adef, overrides, aid)
        plan_template = adef.get("plan_template") if isinstance(adef.get("plan_template"), list) else []
        plan_labels = [str(x) for x in plan_template if x]

        inv = AgentInvocation(
            agent_id=aid,
            user_message=user_message,
            intent=intent_data,
            thread_id=thread_id,
            user_id=user_id,
            location=location,
            limit=limit,
            skills=skills,
        )

        if aid == AGENT_LOCAL_DB:
            return await _invoke_local_db(inv, discover_products_fn, plan_labels)
        if aid == AGENT_UCP:
            return await _invoke_ucp(inv, plan_labels)
        if aid == AGENT_MCP:
            return await _invoke_mcp(inv, plan_labels)
        if aid == AGENT_WEATHER:
            return await _invoke_weather(inv, plan_labels)
        if aid == AGENT_EVENTS:
            return await _invoke_events(inv, plan_labels)
        if aid == AGENT_RESOURCING:
            return await _invoke_resourcing(inv, plan_labels)

        trace: List[AgentOperation] = []
        trace_append(trace, "OBSERVE", "Unknown agent id in workflow; skipped.")
        return AgentResult(id=aid, label=aid, status="failed", summary="Unknown agent", trace=trace)

    tasks = [run_one(aid) for aid in ordered]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    agent_payload: List[Dict[str, Any]] = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            aid = ordered[i] if i < len(ordered) else "unknown"
            agent_payload.append(
                AgentResult(
                    id=aid,
                    label=aid,
                    status="failed",
                    summary=f"Error: {res}",
                    trace=[AgentOperation(phase="OBSERVE", label="Agent raised an unexpected error", detail=str(res), timestamp=time.time())],
                ).model_dump_public()
            )
        else:
            r = res
            adef = agents_by_id.get(r.id, {})
            r.label = str(adef.get("display_name") or r.label or r.id)
            r.user_cancellable = bool(adef.get("user_cancellable", r.user_cancellable))
            r.user_editable = bool(adef.get("user_editable", r.user_editable))
            agent_payload.append(r.model_dump_public())

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    todos: List[Dict[str, Any]] = []
    for i, row in enumerate(agent_payload):
        st = row.get("status")
        if st == "cancelled":
            t_status = "done"
        elif st == "failed":
            t_status = "done"
        elif st == "succeeded":
            t_status = "done"
        else:
            t_status = "done"
        todos.append({"label": f"Scout: {row.get('label', row.get('id'))}", "status": t_status})

    thought_timelines = [
        {
            "label": "Multi-agent coordination",
            "duration_ms": elapsed_ms,
            "detail": f"Ran {len(agent_payload)} scout(s) in parallel for this turn.",
        }
    ]

    approx_tokens_in = message_count * 180 + 400
    approx_tokens_out = 650
    credit_usage = {
        "estimated_input_tokens": approx_tokens_in,
        "estimated_output_tokens": approx_tokens_out,
        "estimated_total_tokens": approx_tokens_in + approx_tokens_out,
        "note": "Heuristic estimate for this turn (Status Narrator / Module 14 visibility).",
    }

    if message_count > 24:
        memory_health = {"status": "near_limit", "label": "Near limit", "detail": "Conversation is long; consider starting a fresh thread for best results."}
    elif message_count > 12:
        memory_health = {"status": "moderate", "label": "Moderate headroom", "detail": "Context usage is healthy; still room to refine."}
    else:
        memory_health = {"status": "healthy", "label": "Plenty of room", "detail": "Context window has ample space for this session."}

    ok = sum(1 for a in agent_payload if a.get("status") == "succeeded")
    narrative = (
        f"I coordinated {len(agent_payload)} scouts ({ok} succeeded). "
        "Inventory, feeds, and context signals are merged for your bundle view."
    )

    return {
        "multi_agent_status": {"agents": agent_payload},
        "todos": todos,
        "thought_timelines": thought_timelines,
        "memory_health": memory_health,
        "credit_usage": credit_usage,
        "multi_agent_narrative": narrative,
    }


def should_run_multi_agent(
    *,
    multi_agent_mode: bool,
    agents_requested: Optional[List[str]],
    intent_type: str,
) -> bool:
    if intent_type not in ("discover", "discover_composite", "browse", "refine_composite"):
        return False
    if multi_agent_mode:
        return True
    if agents_requested:
        return True
    return False


async def attach_multi_agent_to_chat_result(
    out: Dict[str, Any],
    *,
    multi_agent_mode: bool,
    agents_requested: Optional[List[str]],
    cancel_agent_ids: Optional[List[str]],
    agent_skills_overrides: Optional[Dict[str, Any]],
    user_message: str,
    thread_id: Optional[str],
    user_id: Optional[str],
    limit: int,
    discover_products_fn: Callable[..., Awaitable[Dict[str, Any]]],
    message_count: int = 0,
) -> Dict[str, Any]:
    data = out.get("data") or {}
    intent = data.get("intent") or {}
    intent_type = str(intent.get("intent_type") or "")
    if not should_run_multi_agent(
        multi_agent_mode=multi_agent_mode,
        agents_requested=agents_requested,
        intent_type=intent_type,
    ):
        return out
    extra = await run_multi_agent_bundle(
        intent_data=intent if isinstance(intent, dict) else {},
        user_message=user_message,
        thread_id=thread_id,
        user_id=user_id,
        limit=limit,
        discover_products_fn=discover_products_fn,
        agents_requested=agents_requested,
        cancel_agent_ids=cancel_agent_ids,
        agent_skills_overrides=agent_skills_overrides,
        message_count=message_count,
    )
    if not extra:
        return out
    out = dict(out)
    out["multi_agent_status"] = extra.get("multi_agent_status")
    out["todos"] = extra.get("todos")
    out["thought_timelines"] = extra.get("thought_timelines")
    out["memory_health"] = extra.get("memory_health")
    out["credit_usage"] = extra.get("credit_usage")
    out["multi_agent_narrative"] = extra.get("multi_agent_narrative")
    # Also embed in data for clients that only read `data`
    d = dict(out.get("data") or {})
    d["multi_agent_status"] = extra.get("multi_agent_status")
    d["todos"] = extra.get("todos")
    d["thought_timelines"] = extra.get("thought_timelines")
    d["memory_health"] = extra.get("memory_health")
    d["credit_usage"] = extra.get("credit_usage")
    out["data"] = d
    return out
