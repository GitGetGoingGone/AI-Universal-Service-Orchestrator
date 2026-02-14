"""Tool definitions for Agentic AI - actions the agent can execute."""

import logging
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Guardrail limits
MAX_TEXT_LEN = 2000
MAX_QUERY_LEN = 500
MAX_LOCATION_LEN = 200
MAX_MESSAGE_LEN = 1000
MAX_INTENT_DESC_LEN = 2000
MAX_SUMMARY_LEN = 500
LIMIT_MIN = 1
LIMIT_MAX = 100
APPROVAL_TIMEOUT_MIN = 1
APPROVAL_TIMEOUT_MAX = 168
WAIT_EVENT_MAX_LEN = 100

TOOL_DEFS = [
    {
        "name": "resolve_intent",
        "description": "Resolve user's natural language message to structured intent (discover, checkout, track_status, etc.). Use when user sends a new message.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The user's message"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "discover_products",
        "description": "Search for products by query. Use when intent is 'discover' or user wants to find/browse products.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. cakes, flowers)"},
                "limit": {"type": "integer", "description": "Max products to return", "default": 20},
                "location": {"type": "string", "description": "Optional location filter"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "start_orchestration",
        "description": "Start a long-running workflow (e.g. standing intent, multi-step order). Use when user needs async processing.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Initial message/context"},
                "wait_event_name": {"type": "string", "description": "Event to wait for", "default": "WakeUp"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "create_standing_intent",
        "description": "Create a standing intent requiring user approval. Use when user wants condition-based or delayed action (e.g. 'notify me when', 'remind me to', 'schedule for later').",
        "parameters": {
            "type": "object",
            "properties": {
                "intent_description": {"type": "string", "description": "Human-readable description of the standing intent"},
                "approval_timeout_hours": {"type": "integer", "description": "Hours to wait for approval", "default": 24},
                "platform": {"type": "string", "description": "Chat platform (chatgpt, gemini) for webhook push"},
                "thread_id": {"type": "string", "description": "Chat thread ID for approval notification"},
            },
            "required": ["intent_description"],
        },
    },
    {
        "name": "complete",
        "description": "Finish the conversation and return the final response to the user. Use when you have enough information.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Brief summary of what was done"},
            },
        },
    },
]

TOOLS = {t["name"]: t for t in TOOL_DEFS}


def apply_guardrails(name: str, params: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Validate and sanitize tool parameters before execution.
    Returns (sanitized_params, error_message). If error_message is set, do not execute.
    """
    if name not in TOOLS:
        return {}, f"Unknown tool: {name}"

    p = dict(params) if params else {}

    if name == "resolve_intent":
        text = (p.get("text") or "").strip()
        if not text:
            return {}, "resolve_intent requires non-empty text"
        p["text"] = text[:MAX_TEXT_LEN]

    elif name == "discover_products":
        query = (p.get("query") or "").strip()
        # Empty query = browse (allowed)
        p["query"] = query[:MAX_QUERY_LEN] if query else "browse"
        limit = p.get("limit", 20)
        try:
            limit = int(limit) if limit is not None else 20
        except (TypeError, ValueError):
            limit = 20
        p["limit"] = max(LIMIT_MIN, min(LIMIT_MAX, limit))
        loc = p.get("location")
        if loc is not None and isinstance(loc, str):
            p["location"] = loc.strip()[:MAX_LOCATION_LEN] or None

    elif name == "start_orchestration":
        msg = (p.get("message") or "").strip()
        if not msg:
            return {}, "start_orchestration requires non-empty message"
        p["message"] = msg[:MAX_MESSAGE_LEN]
        wait = p.get("wait_event_name", "WakeUp")
        if isinstance(wait, str):
            p["wait_event_name"] = wait.strip()[:WAIT_EVENT_MAX_LEN] or "WakeUp"

    elif name == "create_standing_intent":
        desc = (p.get("intent_description") or "").strip()
        if not desc:
            return {}, "create_standing_intent requires non-empty intent_description"
        p["intent_description"] = desc[:MAX_INTENT_DESC_LEN]
        timeout = p.get("approval_timeout_hours", 24)
        try:
            timeout = int(timeout) if timeout is not None else 24
        except (TypeError, ValueError):
            timeout = 24
        p["approval_timeout_hours"] = max(APPROVAL_TIMEOUT_MIN, min(APPROVAL_TIMEOUT_MAX, timeout))

    elif name == "complete":
        summary = (p.get("summary") or "").strip()
        p["summary"] = summary[:MAX_SUMMARY_LEN] if summary else "Done."

    return p, None


async def execute_tool(
    name: str,
    params: Dict[str, Any],
    *,
    resolve_intent_fn: Optional[Callable] = None,
    discover_products_fn: Optional[Callable] = None,
    start_orchestration_fn: Optional[Callable] = None,
    create_standing_intent_fn: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Execute a tool by name with given parameters.
    Applies guardrails before execution. Callers inject the actual service clients.
    """
    sanitized, err = apply_guardrails(name, params)
    if err:
        logger.warning("Tool guardrail rejected %s: %s", name, err)
        return {"error": err}
    params = sanitized

    if name == "resolve_intent":
        if not resolve_intent_fn:
            return {"error": "resolve_intent not configured"}
        text = params.get("text", "")
        return await resolve_intent_fn(text)

    if name == "discover_products":
        if not discover_products_fn:
            return {"error": "discover_products not configured"}
        return await discover_products_fn(
            query=params.get("query", ""),
            limit=params.get("limit", 20),
            location=params.get("location"),
        )

    if name == "start_orchestration":
        if not start_orchestration_fn:
            return {"error": "start_orchestration not configured"}
        return await start_orchestration_fn(
            message=params.get("message", ""),
            wait_event_name=params.get("wait_event_name", "WakeUp"),
        )

    if name == "create_standing_intent":
        if not create_standing_intent_fn:
            return {"error": "create_standing_intent not configured"}
        return await create_standing_intent_fn(
            intent_description=params.get("intent_description", ""),
            approval_timeout_hours=params.get("approval_timeout_hours", 24),
            platform=params.get("platform"),
            thread_id=params.get("thread_id"),
        )

    if name == "complete":
        return {"status": "complete", "summary": params.get("summary", "")}

    return {"error": f"Unknown tool: {name}"}
