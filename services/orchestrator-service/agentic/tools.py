"""Tool definitions for Agentic AI - actions the agent can execute."""

from typing import Any, Callable, Dict, Optional

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
    Callers inject the actual service clients.
    """
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
