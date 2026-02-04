"""Standardized error handling for all services."""

from .models import (
    ErrorDetail,
    ErrorResponse,
    MachineReadableError,
    create_error_response,
)
from .exceptions import (
    USOException,
    TransientError,
    PermanentError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    RateLimitError,
    ServiceUnavailableError,
)

__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "MachineReadableError",
    "create_error_response",
    "USOException",
    "TransientError",
    "PermanentError",
    "ValidationError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "ConflictError",
    "RateLimitError",
    "ServiceUnavailableError",
]
