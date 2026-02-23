"""JSON-RPC 2.0 endpoint for Business Agent (Discovery). Gateway calls this for discovery/search, discovery/getProduct."""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from db import get_product_by_id
from scout_engine import search as scout_search

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ucp", tags=["UCP RPC"])


def _jsonrpc_error(code: int, message: str, rpc_id: Any = None) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
        "id": rpc_id,
    }


def _jsonrpc_result(result: Any, rpc_id: Any = None) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "result": result, "id": rpc_id}


@router.post("/rpc")
async def ucp_rpc(request: Request) -> JSONResponse:
    """
    JSON-RPC 2.0 endpoint. Methods: discovery/search, discovery/getProduct.
    Body: { "jsonrpc": "2.0", "method": "discovery/search", "params": { "query", "limit", ... }, "id": 1 }
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("UCP RPC: invalid JSON body: %s", e)
        return JSONResponse(status_code=400, content=_jsonrpc_error(-32700, "Parse error", None))

    if not isinstance(body, dict):
        return JSONResponse(status_code=200, content=_jsonrpc_error(-32600, "Invalid Request", None))

    rpc_id = body.get("id")
    method = (body.get("method") or "").strip()
    params = body.get("params") or {}

    if body.get("jsonrpc") != "2.0" or not method:
        return JSONResponse(status_code=200, content=_jsonrpc_error(-32600, "Invalid Request", rpc_id))

    if method == "discovery/search":
        query = (params.get("query") or "").strip()
        limit = int(params.get("limit", 20))
        limit = max(1, min(100, limit))
        partner_id = params.get("filter_partner_id") or params.get("partner_id")
        exclude_partner_id = params.get("exclude_partner_id")
        experience_tag = params.get("experience_tag") or params.get("filter_experience_tag")
        experience_tags = params.get("experience_tags")
        if experience_tag and not experience_tags:
            experience_tags = [experience_tag]

        try:
            products = await scout_search(
                query=query,
                limit=limit,
                partner_id=partner_id,
                exclude_partner_id=exclude_partner_id,
                experience_tag=experience_tag,
                experience_tags=experience_tags,
            )
        except Exception as e:
            logger.warning("discovery/search failed: %s", e)
            return JSONResponse(
                status_code=200,
                content=_jsonrpc_error(-32603, f"Internal error: {e}", rpc_id),
            )
        return JSONResponse(
            status_code=200,
            content=_jsonrpc_result({"products": products, "count": len(products)}, rpc_id),
        )

    if method == "discovery/getProduct":
        product_id = (params.get("id") or params.get("product_id") or "").strip()
        if not product_id:
            return JSONResponse(status_code=200, content=_jsonrpc_error(-32602, "Missing params.id", rpc_id))
        try:
            product = await get_product_by_id(product_id)
        except Exception as e:
            logger.warning("discovery/getProduct failed: %s", e)
            return JSONResponse(status_code=200, content=_jsonrpc_error(-32603, str(e), rpc_id))
        return JSONResponse(status_code=200, content=_jsonrpc_result(product, rpc_id))

    return JSONResponse(status_code=200, content=_jsonrpc_error(-32601, f"Method not found: {method}", rpc_id))
