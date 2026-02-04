"""FastAPI error handling middleware per 02-architecture.md."""

import logging
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .models import create_error_response
from .exceptions import (
    USOException,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    RateLimitError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

# HTTP status mapping per 02-architecture.md
EXCEPTION_STATUS_MAP = {
    ValidationError: 400,
    UnauthorizedError: 401,
    ForbiddenError: 403,
    NotFoundError: 404,
    ConflictError: 409,
    RateLimitError: 429,
    ServiceUnavailableError: 503,
}


def get_request_id(request: Request) -> str:
    """Get or create request ID for correlation."""
    request_id = request.headers.get("X-Request-ID") or getattr(
        request.state, "request_id", None
    )
    if not request_id:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
    return request_id


async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    """Add request ID to all requests for distributed tracing."""
    request_id = get_request_id(request)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def uso_exception_handler(request: Request, exc: USOException) -> JSONResponse:
    """Handle USO exceptions with standardized error format."""
    request_id = get_request_id(request)
    status = EXCEPTION_STATUS_MAP.get(type(exc), 500)

    error_response = create_error_response(
        code=exc.code,
        message=exc.message,
        category=exc.category,
        details=exc.details,
        request_id=request_id,
    )

    logger.warning(
        "USO exception",
        extra={
            "request_id": request_id,
            "error_code": exc.code,
            "message": exc.message,
            "category": exc.category,
        },
    )

    return JSONResponse(
        status_code=status,
        content=error_response.model_dump(by_alias=True),
        headers={
            "X-Request-ID": request_id,
            **(_retry_headers(exc) if exc.details else {}),
        },
    )


def _retry_headers(exc: USOException) -> dict:
    """Add Retry-After header if applicable."""
    headers = {}
    if retry_after := exc.details.get("retry_after"):
        headers["Retry-After"] = str(retry_after)
    return headers


def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions - return 500 with generic message."""
    request_id = get_request_id(request)

    error_response = create_error_response(
        code="USO_500",
        message="An unexpected error occurred. Please try again later.",
        category="system",
        details={"internal": str(exc) if __debug__ else None},
        request_id=request_id,
    )

    logger.exception(
        "Unhandled exception",
        extra={"request_id": request_id},
        exc_info=exc,
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(by_alias=True),
        headers={"X-Request-ID": request_id},
    )
