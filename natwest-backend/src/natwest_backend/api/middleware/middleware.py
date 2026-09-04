import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .observability import new_request_id, now_ms, request_id_ctx

logger = structlog.get_logger("api")


def _get_auth_log_fields(request: Request) -> dict[str, str]:
    """
    Return auth fields for logging when the request is authenticated.
    """
    auth_context = getattr(request.state, "auth_context", None)
    if auth_context is None:
        return {}

    return {
        "username": auth_context.username,
        "role": auth_context.role.value,
        "user_id": auth_context.app_user_id,
    }


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Log safe request metadata for each API call.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Attach a request ID and emit structured request logs.
        """
        request_id = request.headers.get("x-request-id") or new_request_id()
        request_id_ctx.set(request_id)

        start_ms = now_ms()
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)

        try:
            response = await call_next(request)
            duration_ms = round(now_ms() - start_ms, 2)
            response.headers.setdefault("x-request-id", request_id)
            auth_fields = _get_auth_log_fields(request)

            logger.info(
                "http_request_completed",
                method=request.method,
                path=request.url.path,
                route=route_path,
                query=str(request.url.query),
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_host=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                content_length=response.headers.get("content-length"),
                **auth_fields,
            )

            return response

        except Exception as exc:
            duration_ms = round(now_ms() - start_ms, 2)
            auth_fields = _get_auth_log_fields(request)

            logger.exception(
                "http_request_failed",
                method=request.method,
                path=request.url.path,
                route=route_path,
                query=str(request.url.query),
                duration_ms=duration_ms,
                client_host=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                error=str(exc),
                **auth_fields,
            )

            raise
