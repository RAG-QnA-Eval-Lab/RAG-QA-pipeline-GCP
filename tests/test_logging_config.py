"""구조화 JSON 로깅 테스트."""

from __future__ import annotations

import json
import logging

from src.api.logging_config import CloudRunJsonFormatter, log_structured, setup_json_logging


class TestCloudRunJsonFormatter:
    def test_format_produces_valid_json(self) -> None:
        formatter = CloudRunJsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=(),
            exc_info=None,
        )
        line = formatter.format(record)
        parsed = json.loads(line)
        assert parsed["severity"] == "INFO"
        assert parsed["message"] == "hello"
        assert parsed["logger"] == "test"
        assert "timestamp" in parsed

    def test_severity_mapping(self) -> None:
        formatter = CloudRunJsonFormatter()
        for level, expected in [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]:
            record = logging.LogRecord("t", level, "", 0, "msg", (), None)
            parsed = json.loads(formatter.format(record))
            assert parsed["severity"] == expected

    def test_structured_fields_merged(self) -> None:
        formatter = CloudRunJsonFormatter()
        record = logging.LogRecord("t", logging.INFO, "", 0, "req", (), None)
        record.structured = {"model": "gpt-4o", "latency_ms": 123}  # type: ignore[attr-defined]
        parsed = json.loads(formatter.format(record))
        assert parsed["model"] == "gpt-4o"
        assert parsed["latency_ms"] == 123
        assert parsed["message"] == "req"

    def test_exception_included(self) -> None:
        formatter = CloudRunJsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            record = logging.LogRecord("t", logging.ERROR, "", 0, "err", (), sys.exc_info())
        parsed = json.loads(formatter.format(record))
        assert "traceback" in parsed
        assert "ValueError" in parsed["traceback"]

    def test_korean_text_preserved(self) -> None:
        formatter = CloudRunJsonFormatter()
        record = logging.LogRecord("t", logging.INFO, "", 0, "청년 정책 검색", (), None)
        parsed = json.loads(formatter.format(record))
        assert parsed["message"] == "청년 정책 검색"


class TestSetupJsonLogging:
    def test_replaces_root_handlers(self) -> None:
        setup_json_logging()
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0].formatter, CloudRunJsonFormatter)

    def test_uvicorn_loggers_propagate(self) -> None:
        setup_json_logging()
        assert logging.getLogger("uvicorn.access").propagate is True
        assert logging.getLogger("uvicorn.error").propagate is True


class TestLogStructured:
    def test_log_structured_emits_json(self, capfd: object) -> None:
        setup_json_logging()
        test_logger = logging.getLogger("test.structured")
        log_structured(
            test_logger,
            logging.INFO,
            "rag_request",
            model="gemini-flash",
            tokens_in=100,
            tokens_out=50,
        )
        import sys

        sys.stdout.flush()
