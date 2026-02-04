"""Error response models per 02-architecture.md Error Handling standards."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Structured error details for API responses."""

    code: str = Field(..., description="Error code in format MODULE_NUMBER")
    message: str = Field(..., description="Human-readable error message")
    category: str = Field(
        ...,
        description="Error category: transient, permanent, user, system",
    )
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional context (partner_id, retry_after, etc.)",
    )
    request_id: Optional[str] = Field(default=None, description="Request correlation ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Error timestamp in ISO 8601",
    )


class MachineReadableError(BaseModel):
    """JSON-LD machine-readable error for AI agent consumption."""

    context: str = Field(
        default="https://schema.org",
        alias="@context",
        description="JSON-LD context",
    )
    type: str = Field(default="Error", alias="@type", description="Schema type")
    errorCode: str = Field(..., description="Error code")
    description: str = Field(..., description="Error description")

    class Config:
        populate_by_name = True


class ErrorResponse(BaseModel):
    """Standardized error response schema."""

    error: ErrorDetail
    machine_readable: Optional[MachineReadableError] = Field(
        default=None,
        description="Machine-readable block for LLM consumption",
    )


def create_error_response(
    code: str,
    message: str,
    category: str = "system",
    details: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None,
    include_machine_readable: bool = True,
) -> ErrorResponse:
    """Create standardized error response."""
    error_detail = ErrorDetail(
        code=code,
        message=message,
        category=category,
        details=details,
        request_id=request_id,
    )
    machine_readable = None
    if include_machine_readable:
        machine_readable = MachineReadableError(
            errorCode=code,
            description=message,
        )
    return ErrorResponse(error=error_detail, machine_readable=machine_readable)
