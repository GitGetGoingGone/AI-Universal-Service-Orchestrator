"""Retry utilities per 02-architecture.md Retry Policies."""

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Retry configuration per service (from 02-architecture.md)
RETRY_CONFIG = {
    "scout_engine": {
        "max_attempts": 3,
        "initial_delay": 1.0,
        "max_delay": 10.0,
        "exponential_base": 2.0,
    },
    "intent_resolver": {
        "max_attempts": 2,
        "initial_delay": 2.0,
        "max_delay": 8.0,
        "exponential_base": 2.0,
    },
    "payment_service": {
        "max_attempts": 3,
        "initial_delay": 5.0,
        "max_delay": 30.0,
        "exponential_base": 2.0,
    },
    "default": {
        "max_attempts": 3,
        "initial_delay": 1.0,
        "max_delay": 10.0,
        "exponential_base": 2.0,
    },
}


def create_retry_decorator(
    service: str = "default",
    retryable_exceptions: tuple = (Exception,),
):
    """Create retry decorator for a service."""
    config = RETRY_CONFIG.get(service, RETRY_CONFIG["default"])
    return retry(
        stop=stop_after_attempt(config["max_attempts"]),
        wait=wait_exponential(
            multiplier=config["initial_delay"],
            min=config["initial_delay"],
            max=config["max_delay"],
        ),
        retry=retry_if_exception_type(retryable_exceptions),
        reraise=True,
    )
