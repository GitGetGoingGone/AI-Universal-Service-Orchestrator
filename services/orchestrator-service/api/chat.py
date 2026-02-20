"""Chat endpoint - Agentic AI with Intent → Discovery orchestration."""

import asyncio
import json
from typing import Any, Callable, Dict, List, Literal, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from clients import (
    resolve_intent_with_fallback,
    discover_products,
    start_orchestration,
    create_standing_intent_via_api,
    register_thread_mapping,
)
from agentic.loop import run_agentic_loop
from agentic.response import generate_engagement_response
from packages.shared.utils.api_response import chat_first_response, request_id_from_request
from packages.shared.json_ld.error import error_ld

router = APIRouter(prefix="/api/v1", tags=["Chat"])


class ChatRequest(BaseModel):
    """Request body for chat (natural language)."""

    text: str = Field(..., min_length=1, max_length=2000, description="User message")
    messages: Optional[List[Dict[str, Any]]] = Field(None, description="Conversation history [{role, content}] for refinement")
    user_id: Optional[str] = Field(None, description="Optional platform user UUID (or resolved from platform_user_id when linked)")
    platform_user_id: Optional[str] = Field(None, description="Platform identity (e.g. ChatGPT/Gemini user id); resolved to user_id via account_links")
    limit: int = Field(20, ge=1, le=100, description="Max products when discover")
    thread_id: Optional[str] = Field(None, description="Chat thread ID for webhook push (ChatGPT/Gemini)")
    platform: Optional[Literal["chatgpt", "gemini", "web"]] = Field(None, description="Platform for webhook push (web = unified chat app)")
    partner_id: Optional[str] = Field(None, description="Filter products to this partner (for embed/white-label)")
    bundle_id: Optional[str] = Field(None, description="Thread's bundle ID - use for order context, never ask user")
    order_id: Optional[str] = Field(None, description="Thread's paid order ID - use for track/support, never ask user")


async def _stream_chat_events(
    *,
    body: ChatRequest,
    agentic: bool,
    user_id: Optional[str],
    _resolve: Callable,
    _discover: Callable,
    _create_standing_intent: Callable,
    adaptive_cards: Optional[bool],
    request_id: str,
):
    """Async generator yielding SSE events for streaming chat."""
    queue: asyncio.Queue = asyncio.Queue()
    result_holder: List[Optional[Dict]] = [None]
    err_holder: List[Optional[Exception]] = [None]

    async def on_thinking(msg: str, ctx: Optional[Dict]) -> None:
        await queue.put(("thinking", {"text": msg, "step": (ctx or {}).get("step", "")}))

    async def run_loop() -> None:
        try:
            r = await run_agentic_loop(
                body.text,
                user_id=user_id,
                limit=body.limit,
                resolve_intent_fn=_resolve,
                discover_products_fn=_discover,
                start_orchestration_fn=start_orchestration,
                create_standing_intent_fn=_create_standing_intent,
                use_agentic=agentic,
                platform=body.platform,
                thread_id=body.thread_id,
                messages=body.messages,
                bundle_id=body.bundle_id,
                order_id=body.order_id,
                on_thinking=on_thinking,
            )
            result_holder[0] = r
        except Exception as e:
            err_holder[0] = e
        finally:
            await queue.put(("complete", None))

    loop_task = asyncio.create_task(run_loop())

    while True:
        try:
            event_type, data = await asyncio.wait_for(queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            yield "event: ping\ndata: {}\n\n"
            continue
        if event_type == "thinking":
            yield f"event: thinking\ndata: {json.dumps(data)}\n\n"
        elif event_type == "complete":
            break

    await loop_task

    if err_holder[0]:
        yield f"event: error\ndata: {json.dumps({'error': str(err_holder[0])})}\n\n"
        return

    result = result_holder[0]
    if not result:
        yield f"event: error\ndata: {json.dumps({'error': 'No result'})}\n\n"
        return

    if "error" in result:
        yield f"event: error\ndata: {json.dumps({'error': result['error']})}\n\n"
        return

    use_adaptive_cards = True
    if adaptive_cards is not None:
        use_adaptive_cards = adaptive_cards
    else:
        try:
            from db import get_adaptive_cards_setting
            use_adaptive_cards = await get_adaptive_cards_setting(
                partner_id=body.partner_id,
                user_id=user_id,
            )
        except Exception:
            pass

    adaptive_card = result.get("adaptive_card") if use_adaptive_cards else None
    # Do NOT inject agent_reasoning into the card — it's internal and not user-facing

    planner_message = (result.get("planner_complete_message") or "").strip()
    generic_messages = ("processed your request.", "processed your request", "done.", "done", "complete.", "complete")
    if planner_message and planner_message.lower() not in generic_messages:
        summary = planner_message
    else:
        summary = await generate_engagement_response(body.text, result)
        if not summary:
            summary = _build_summary(result)
    if not summary:
        summary = "I'm here to help. What would you like to explore?"
    response_data = chat_first_response(
        data=result.get("data", {}),
        machine_readable=result.get("machine_readable", {}),
        adaptive_card=adaptive_card,
        request_id=request_id,
        summary=summary or "I'm here to help. What would you like to explore?",
        agent_reasoning=result.get("agent_reasoning", []),
    )
    body_json = json.dumps(response_data, default=str)
    yield f"event: done\ndata: {body_json}\n\n"


@router.post("/chat")
async def chat(
    request: Request,
    body: ChatRequest,
    agentic: bool = Query(
        True,
        description="Use agentic AI planning (LLM-based). Falls back to direct flow when disabled or LLM unavailable.",
    ),
    adaptive_cards: Optional[bool] = Query(
        None,
        description="Override adaptive cards: true=show, false=conversational only. If omitted, uses platform/partner/user settings.",
    ),
    stream: bool = Query(
        False,
        description="When true, return SSE stream with thinking events and final done event.",
    ),
):
    """
    AI Agents Chat Entry Point + Agentic AI.

    Single endpoint for ChatGPT/Gemini: send user message, get intent + products.
    When agentic=True (default): uses LLM to plan and execute (resolve_intent → discover_products).
    When agentic=False or LLM unavailable: direct intent→discover flow.
    """
    request_id = request_id_from_request(request)

    # Resolve user_id: use body.user_id, or resolve from account_links when platform_user_id + platform sent
    user_id = body.user_id
    if not user_id and body.platform_user_id and body.platform:
        try:
            from db import get_user_id_by_platform_user
            user_id = get_user_id_by_platform_user(body.platform, body.platform_user_id)
        except Exception:
            pass

    # Register thread mapping when ChatGPT/Gemini pass thread_id + platform (enables webhook push)
    if body.thread_id and body.platform:
        await register_thread_mapping(
            platform=body.platform,
            thread_id=body.thread_id,
            user_id=user_id,
            platform_user_id=body.platform_user_id,
        )

    # Resolve intent with user_id captured; uses local fallback when Intent service unavailable
    # When platform is chatgpt/gemini and force_model_based_intent, use LLM only (no heuristic fallback)
    force_model = False
    if body.platform in ("chatgpt", "gemini"):
        try:
            from api.admin import _get_platform_config
            cfg = _get_platform_config() or {}
            force_model = bool(cfg.get("force_model_based_intent"))
        except Exception:
            pass

    async def _resolve(
        text: str,
        last_suggestion: Optional[str] = None,
        recent_conversation: Optional[list] = None,
        probe_count: Optional[int] = None,
        thread_context: Optional[dict] = None,
    ):
        return await resolve_intent_with_fallback(
            text,
            user_id=user_id,
            last_suggestion=last_suggestion,
            recent_conversation=recent_conversation,
            probe_count=probe_count,
            thread_context=thread_context,
            force_model=force_model,
        )

    async def _discover(query: str, limit: int = 20, location: Optional[str] = None, partner_id: Optional[str] = None, exclude_partner_id: Optional[str] = None, budget_max: Optional[int] = None):
        return await discover_products(
            query=query,
            limit=limit,
            location=location,
            partner_id=partner_id or body.partner_id,
            exclude_partner_id=exclude_partner_id,
            budget_max=budget_max,
        )

    async def _create_standing_intent(
        intent_description: str,
        approval_timeout_hours: int = 24,
        platform: Optional[str] = None,
        thread_id: Optional[str] = None,
    ):
        return await create_standing_intent_via_api(
            intent_description=intent_description,
            approval_timeout_hours=approval_timeout_hours,
            platform=platform,
            thread_id=thread_id,
            user_id=user_id,
        )

    if stream:
        return StreamingResponse(
            _stream_chat_events(
                body=body,
                agentic=agentic,
                user_id=user_id,
                _resolve=_resolve,
                _discover=_discover,
                _create_standing_intent=_create_standing_intent,
                adaptive_cards=adaptive_cards,
                request_id=request_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        result = await run_agentic_loop(
            body.text,
            user_id=user_id,
            limit=body.limit,
            resolve_intent_fn=_resolve,
            discover_products_fn=_discover,
            start_orchestration_fn=start_orchestration,
            create_standing_intent_fn=_create_standing_intent,
            use_agentic=agentic,
            platform=body.platform,
            thread_id=body.thread_id,
            messages=body.messages,
            bundle_id=body.bundle_id,
            order_id=body.order_id,
        )
    except Exception as e:
        return chat_first_response(
            data={"intent": None, "products": None, "error": str(e)},
            machine_readable=error_ld(str(e)),
            request_id=request_id,
            summary=f"Sorry, I couldn't complete your request: {e}",
        )

    if "error" in result:
        return chat_first_response(
            data={"intent": None, "products": None, "error": result["error"]},
            machine_readable=error_ld(result["error"]),
            request_id=request_id,
            summary=f"Sorry, I couldn't complete your request: {result['error']}",
        )

    # Response style control: conversational only vs adaptive cards
    use_adaptive_cards = True
    if adaptive_cards is not None:
        use_adaptive_cards = adaptive_cards
    else:
        try:
            from db import get_adaptive_cards_setting
            use_adaptive_cards = await get_adaptive_cards_setting(
                partner_id=body.partner_id,
                user_id=user_id,
            )
        except Exception:
            pass

    adaptive_card = result.get("adaptive_card") if use_adaptive_cards else None
    # Do NOT inject agent_reasoning into the card — it's internal and not user-facing

    # Prefer planner message only when it's specific (e.g. probing questions).
    # For generic fallbacks ("Processed your request.", "Done."), always use engagement response
    # so the LLM can generate natural, empathetic replies (e.g. "I know, it's a lot to take in!").
    planner_message = (result.get("planner_complete_message") or "").strip()
    generic_messages = ("processed your request.", "processed your request", "done.", "done", "complete.", "complete")
    if planner_message and planner_message.lower() not in generic_messages:
        summary = planner_message
    else:
        summary = await generate_engagement_response(body.text, result)
        if not summary:
            summary = _build_summary(result)
    return chat_first_response(
        data=result.get("data", {}),
        machine_readable=result.get("machine_readable", {}),
        adaptive_card=adaptive_card,
        request_id=request_id,
        summary=summary,
        agent_reasoning=result.get("agent_reasoning", []),
    )


def _build_summary(result: dict) -> str:
    """Build human-readable summary for ChatGPT/Gemini display."""
    if result.get("error"):
        return f"Sorry, I couldn't complete your request: {result['error']}"

    data = result.get("data", {})
    intent = data.get("intent") or {}
    intent_type = intent.get("intent_type", "")
    engagement = data.get("engagement") or {}
    products = data.get("products") or {}
    product_list = products.get("products") or []
    count = products.get("count", len(product_list))

    if count == 0:
        query = (intent.get("search_query") or "").strip() or "your search"
        return f"No products found for '{query}'."

    # For discover_composite with bundle: narrative from actual bundle items only (no hardcoded limo/flowers/restaurant)
    suggested = engagement.get("suggested_bundle_options") or []
    if intent_type == "discover_composite" and suggested:
        opt = suggested[0]
        names = opt.get("product_names") or []
        total = opt.get("total_price")
        curr = opt.get("currency", "USD")
        exp = products.get("experience_name", "experience")
        exp_title = str(exp).replace("_", " ").title()
        total_str = f"{curr} {total:.2f}" if total is not None else ""
        # Describe only what's in the bundle (respects "no limo" / removed categories)
        if not names:
            intro = f"Your perfect {exp_title} is ready."
        elif len(names) == 1:
            intro = f"Your perfect {exp_title}: {names[0]}."
        else:
            intro = f"Your perfect {exp_title}: {' — '.join(names)}."
        return (
            f"{intro} "
            f"To place this order I'll need pickup time, pickup address, and delivery address—you can share them in the chat now or when you tap Add this bundle. "
            f"Total: {total_str}. Add this bundle when you're ready."
        )

    parts = []
    for p in product_list[:5]:
        name = p.get("name", "Product")
        price = p.get("price")
        currency = p.get("currency", "USD")
        if price is not None:
            parts.append(f"{name} ({currency} {price:.2f})")
        else:
            parts.append(name)
    if count > 5:
        parts.append(f"... and {count - 5} more")
    return f"Found {count} product(s): " + ", ".join(parts)


@router.get("/agentic-consent")
async def agentic_consent():
    """
    Agentic consent and agency boundaries (per Pillar 2).
    Returns config for what the agent is allowed to do on behalf of the user.
    """
    return {
        "scope": "discover_and_browse",
        "allowed_actions": ["resolve_intent", "discover_products", "start_orchestration", "create_standing_intent"],
        "requires_confirmation": ["checkout", "add_to_bundle"],
        "message": "Agent can discover products and start workflows. Checkout and add-to-bundle require user confirmation.",
    }


@router.get("/agentic-handoff")
async def agentic_handoff():
    """
    Agentic handoff config (SSO 2.0) for ChatGPT/Gemini → custom UI.
    Returns Clerk config when configured.
    """
    from config import settings

    if not settings.agentic_handoff_configured:
        return {
            "configured": False,
            "publishable_key": None,
            "sign_in_url": None,
            "message": "Configure CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY for agentic handoff.",
        }
    return {
        "configured": True,
        "publishable_key": settings.clerk_publishable_key,
        "sign_in_url": "/sign-in",
    }
