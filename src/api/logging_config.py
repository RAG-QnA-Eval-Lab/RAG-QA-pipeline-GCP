"""Cloud Run 구조화 JSON 로깅 설정.

Cloud Run은 stdout의 각 JSON 라인을 Cloud Logging에서 자동 파싱한다.
``severity`` 필드가 있으면 로그 레벨로 매핑되고,
나머지 필드는 jsonPayload로 인덱싱되어 쿼리 가능해진다.

외부 의존성 없이 표준 라이브러리만 사용한다.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class CloudRunJsonFormatter(logging.Formatter):
    """Cloud Logging이 인식하는 JSON 한 줄을 출력하는 포매터."""

    _LEVEL_TO_SEVERITY = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
    }

    def format(self, record: logging.Record) -> str:
        payload: dict = {
            "severity": self._LEVEL_TO_SEVERITY.get(record.levelno, "DEFAULT"),
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
        }

        if record.exc_info and record.exc_info[1] is not None:
            payload["traceback"] = self.formatException(record.exc_info)

        if hasattr(record, "structured") and isinstance(record.structured, dict):
            payload.update(record.structured)

        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_json_logging(*, level: int = logging.INFO) -> None:
    """루트 로거에 JSON 포매터를 설정한다. 애플리케이션 시작 시 한 번만 호출."""
    root = logging.getLogger()
    root.setLevel(level)

    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudRunJsonFormatter())
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.error").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = True
    logging.getLogger("uvicorn.error").propagate = True


def log_structured(logger: logging.Logger, level: int, message: str, **fields: object) -> None:
    """구조화 필드를 포함한 로그를 남긴다. Cloud Logging jsonPayload에 인덱싱된다."""
    record = logger.makeRecord(
        name=logger.name,
        level=level,
        fn="",
        lno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    record.structured = fields  # type: ignore[attr-defined]
    logger.handle(record)
