"""Custom exceptions with error codes per 02-architecture.md."""

from typing import Any, Optional


class USOException(Exception):
    """Base exception for AI Universal Service Orchestrator."""

    def __init__(
        self,
        message: str,
        code: str = "USO_000",
        category: str = "system",
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.category = category
        self.details = details or {}
        super().__init__(message)


class TransientError(USOException):
    """Retryable errors: network timeouts, temporary unavailability."""

    def __init__(
        self,
        message: str,
        code: str = "USO_001",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, "transient", details)


class PermanentError(USOException):
    """Non-retryable errors: invalid input, auth failures."""

    def __init__(
        self,
        message: str,
        code: str = "USO_002",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, "permanent", details)


class ValidationError(PermanentError):
    """Validation failures - 400 Bad Request."""

    def __init__(
        self,
        message: str,
        code: str = "USO_400",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class NotFoundError(PermanentError):
    """Resource not found - 404."""

    def __init__(
        self,
        message: str,
        code: str = "USO_404",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class UnauthorizedError(PermanentError):
    """Authentication failures - 401."""

    def __init__(
        self,
        message: str,
        code: str = "USO_401",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class ForbiddenError(PermanentError):
    """Authorization failures - 403."""

    def __init__(
        self,
        message: str,
        code: str = "USO_403",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class ConflictError(PermanentError):
    """Business rule violations - 409."""

    def __init__(
        self,
        message: str,
        code: str = "USO_409",
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, code, details)


class RateLimitError(TransientError):
    """Rate limit exceeded - 429."""

    def __init__(
        self,
        message: str,
        code: str = "USO_429",
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        d = details or {}
        if retry_after is not None:
            d["retry_after"] = retry_after
        super().__init__(message, code, d)


class ServiceUnavailableError(TransientError):
    """Service temporarily unavailable - 503."""

    def __init__(
        self,
        message: str,
        code: str = "USO_503",
        retry_after: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        d = details or {}
        if retry_after is not None:
            d["retry_after"] = retry_after
        super().__init__(message, code, d)
