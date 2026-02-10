"""Schema.org JSON-LD for Error (machine_readable errors)."""

from typing import Any, Dict, Optional


def error_ld(
    description: str,
    error_code: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Error as Schema.org (Thing with error semantics for AI agents)."""
    out: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Thing",
        "name": "Error",
        "description": description,
    }
    if error_code:
        out["identifier"] = error_code
    out.update(kwargs)
    return out
