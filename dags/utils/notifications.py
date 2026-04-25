"""Airflow 실패 알림 콜백."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def on_failure_callback(context: dict) -> None:
    """DAG task 실패 시 로그 기록.

    향후 Slack/Email 알림으로 확장 가능.
    """
    dag_id = context.get("dag", {}).dag_id if context.get("dag") else "unknown"
    task_id = context.get("task_instance", {}).task_id if context.get("task_instance") else "unknown"
    execution_date = context.get("execution_date", "unknown")
    exception = context.get("exception", "N/A")

    logger.error(
        "DAG 실패 알림 | dag=%s | task=%s | date=%s | error=%s",
        dag_id,
        task_id,
        execution_date,
        exception,
    )
