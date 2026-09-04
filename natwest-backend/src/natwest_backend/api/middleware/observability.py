import contextvars
import logging
import sys
import time
import uuid
from collections.abc import MutableMapping
from typing import Any

import structlog

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def add_request_id(
    _: Any,
    __: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """
    Add the current request ID to each structured log event.
    """
    request_id = request_id_ctx.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog for JSON API logs.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            add_request_id,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def new_request_id() -> str:
    """
    Generate a request ID for correlation across logs.
    """
    return str(uuid.uuid4())


def now_ms() -> float:
    """
    Return a high-resolution timestamp in milliseconds.
    """
    return time.perf_counter() * 1000
