"""
Chat-First API response standard (Pillar 6).
Every API response includes: data, machine_readable (JSON-LD), adaptive_card (optional), metadata.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional


def request_id_from_request(request: Any) -> str:
    """Get request_id from FastAPI request state or generate one."""
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def chat_first_response(
    data: Any,
    *,
    machine_readable: Optional[Dict[str, Any]] = None,
    adaptive_card: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    summary: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    """
    Build standard Chat-First response per Pillar 6.

    Returns:
        {
            "data": ...,
            "machine_readable": { "@context": "https://schema.org", "@type": ..., ... },
            "adaptive_card": { ... } or null,
            "metadata": { "api_version", "timestamp", "request_id" },
            "summary": ... (optional),
        }
    """
    payload: Dict[str, Any] = {
        "data": data,
        "machine_readable": machine_readable if machine_readable is not None else {},
        "adaptive_card": adaptive_card,
        "metadata": {
            "api_version": "v1",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id or str(uuid.uuid4()),
        },
    }
    if summary is not None:
        payload["summary"] = summary
    payload.update(extra)
    return payload
