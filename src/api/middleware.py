"""요청 로깅 미들웨어."""

from __future__ import annotations

import logging
import time
import traceback
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.api.monitoring import get_monitoring_client

logger = logging.getLogger("api.access")


def _structured_log(log: logging.Logger, payload: dict) -> None:
    """Cloud Run 구조화 로깅 — severity 필드를 Python 로그 레벨에 매핑."""
    severity = payload.get("severity", "INFO")
    level = {"ERROR": logging.ERROR, "WARNING": logging.WARNING}.get(severity, logging.INFO)
    log.log(level, "%s", payload)


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
            _structured_log(logger, {
                "severity": "ERROR",
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": 500,
                "latency_ms": elapsed_ms,
                "traceback": traceback.format_exc(),
            })
            get_monitoring_client().record_request(request.url.path, request.method, 500, elapsed_ms)
            raise

        elapsed_ms = round((time.monotonic() - start) * 1000)
        _structured_log(logger, {
            "severity": "INFO" if status_code < 400 else "WARNING",
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": status_code,
            "latency_ms": elapsed_ms,
        })
        get_monitoring_client().record_request(request.url.path, request.method, status_code, elapsed_ms)
        response.headers["X-Request-ID"] = request_id
        return response
