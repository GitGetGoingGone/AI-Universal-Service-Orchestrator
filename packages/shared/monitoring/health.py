"""Health check endpoints per 07-project-operations.md."""

from enum import Enum
from typing import Awaitable, Callable, List, Optional, Tuple

from fastapi import APIRouter, Request
from pydantic import BaseModel


class DependencyStatus(str, Enum):
    """Status of a dependency check."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class DependencyCheck(BaseModel):
    """Result of a single dependency check."""

    name: str
    status: DependencyStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str  # "healthy" | "unhealthy" | "degraded"
    service: str
    version: str
    dependencies: Optional[List[DependencyCheck]] = None


class HealthChecker:
    """Health check manager with dependency checks."""

    def __init__(self, service_name: str, version: str = "0.1.0"):
        self.service_name = service_name
        self.version = version
        self._checks: List[Tuple[str, Callable[[], Awaitable[DependencyCheck]]]] = []

    def add_check(self, name: str, check: Callable[[], Awaitable[DependencyCheck]]):
        """Register a dependency check."""
        self._checks.append((name, check))

    async def check_dependencies(self) -> List[DependencyCheck]:
        """Run all dependency checks."""
        results = []
        for name, check_fn in self._checks:
            try:
                result = await check_fn()
                results.append(result)
            except Exception as e:
                results.append(
                    DependencyCheck(
                        name=name,
                        status=DependencyStatus.UNHEALTHY,
                        message=str(e),
                    )
                )
        return results

    async def readiness(self, request: Request) -> dict:
        """Readiness probe - verify all dependencies."""
        dependencies = await self.check_dependencies()
        statuses = [d.status for d in dependencies]
        if DependencyStatus.UNHEALTHY in statuses:
            overall = "unhealthy"
        elif DependencyStatus.DEGRADED in statuses:
            overall = "degraded"
        elif all(s == DependencyStatus.HEALTHY for s in statuses):
            overall = "healthy"
        else:
            overall = "degraded"

        return {
            "status": overall,
            "service": self.service_name,
            "version": self.version,
            "dependencies": [d.model_dump() for d in dependencies],
        }


def health_router(health_checker: HealthChecker) -> APIRouter:
    """Create FastAPI router with /health and /ready endpoints."""
    router = APIRouter(tags=["Health"])

    @router.get("/health")
    async def health():
        """Liveness probe - is the process running."""
        return {
            "status": "healthy",
            "service": health_checker.service_name,
            "version": health_checker.version,
        }

    @router.get("/ready")
    async def ready(request: Request):
        """Readiness probe - can the service accept traffic."""
        return await health_checker.readiness(request)

    return router
