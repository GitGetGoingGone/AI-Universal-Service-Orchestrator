"""Tests for Agentic AI chat endpoint."""

import pytest
from unittest.mock import AsyncMock

# Add orchestrator-service to path (run from project root)
import sys
from pathlib import Path

_orchestrator = Path(__file__).resolve().parents[1] / "services" / "orchestrator-service"
sys.path.insert(0, str(_orchestrator))


@pytest.mark.asyncio
async def test_agentic_loop_fallback():
    """Test agentic loop with fallback (no LLM) - direct flow."""
    from agentic.loop import run_agentic_loop

    async def resolve(text):
        return {
            "data": {"intent_type": "discover", "search_query": "cakes", "confidence_score": 0.9}
        }

    async def discover(query, limit=20, location=None):
        return {
            "data": {"products": [{"name": "Cake"}], "count": 1},
            "adaptive_card": {},
            "machine_readable": {},
        }

    result = await run_agentic_loop(
        "find cakes",
        resolve_intent_fn=resolve,
        discover_products_fn=discover,
        use_agentic=False,
    )

    assert "data" in result
    assert result["data"]["intent"]["intent_type"] == "discover"
    assert result["data"]["products"]["count"] == 1


@pytest.mark.asyncio
async def test_agentic_tools_execute():
    """Test tool execution."""
    from agentic.tools import execute_tool

    async def resolve(text):
        return {"data": {"intent_type": "discover", "search_query": "flowers"}}

    result = await execute_tool(
        "resolve_intent",
        {"text": "I want flowers"},
        resolve_intent_fn=resolve,
    )
    assert result["data"]["intent_type"] == "discover"
    assert result["data"]["search_query"] == "flowers"


@pytest.mark.asyncio
async def test_agentic_fallback_plan():
    """Test fallback planner returns resolve_intent then discover."""
    from agentic.planner import _fallback_plan

    # First iteration: resolve intent
    plan = _fallback_plan("find cakes", {"iteration": 0})
    assert plan["action"] == "tool"
    assert plan["tool_name"] == "resolve_intent"

    # Second iteration with discover intent: discover products
    plan = _fallback_plan(
        "find cakes",
        {
            "iteration": 1,
            "last_tool_result": {"data": {"intent_type": "discover", "search_query": "cakes"}},
        },
    )
    assert plan["action"] == "tool"
    assert plan["tool_name"] == "discover_products"
    assert plan["tool_args"]["query"] == "cakes"
