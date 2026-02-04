"""Structured logging per 07-project-operations.md."""

import logging
import sys
from typing import Any, Optional

# Structured log format from plan
LOG_FORMAT = (
    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
    '"service": "%(service)s", "request_id": "%(request_id)s", '
    '"message": "%(message)s", "context": %(context)s}'
)


def configure_logging(
    service_name: str = "uso",
    level: str = "INFO",
    json_format: bool = True,
) -> None:
    """Configure structured logging for the service."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper()))

    if root.handlers:
        root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    if json_format:
        handler.setFormatter(
            StructuredFormatter(service_name=service_name)
        )
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
        )

    root.addHandler(handler)


class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter."""

    def __init__(self, service_name: str = "uso", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime

        log_obj = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "request_id": getattr(record, "request_id", None),
            "message": record.getMessage(),
            "context": getattr(record, "context", {}),
        }
        if record.exc_info:
            log_obj["stack_trace"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, default=str)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    request_id: Optional[str] = None,
    **context: Any,
) -> None:
    """Log with structured context."""
    extra = {"request_id": request_id, "context": context}
    logger.log(level, message, extra=extra)
