"""요청 로깅 미들웨어."""

from __future__ import annotations

import logging
import time
import traceback
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.api.logging_config import log_structured
from src.api.monitoring import get_monitoring_client

logger = logging.getLogger("api.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id
        start = time.monotonic()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            elapsed_ms = round((time.monotonic() - start) * 1000)
            log_structured(
                logger,
                logging.ERROR,
                "http_request",
                event="http_request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status=500,
                latency_ms=elapsed_ms,
                traceback=traceback.format_exc(),
            )
            get_monitoring_client().record_request(request.url.path, request.method, 500, elapsed_ms)
            raise

        elapsed_ms = round((time.monotonic() - start) * 1000)
        level = logging.INFO if status_code < 400 else logging.WARNING
        log_structured(
            logger,
            level,
            "http_request",
            event="http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=status_code,
            latency_ms=elapsed_ms,
        )
        get_monitoring_client().record_request(request.url.path, request.method, status_code, elapsed_ms)
        response.headers["X-Request-ID"] = request_id
        return response
