"""요청 로깅 미들웨어."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("api.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id
        start = time.monotonic()

        response = await call_next(request)

        elapsed_ms = round((time.monotonic() - start) * 1000)
        logger.info(
            "%s %s %d %dms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": elapsed_ms,
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response
