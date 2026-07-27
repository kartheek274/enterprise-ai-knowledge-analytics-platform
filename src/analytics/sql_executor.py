"""Validated SQL execution service."""

import logging
import time

from src.analytics.exceptions import SQLExecutionError
from src.analytics.models import SQLExecutionResult
from src.common.database.service import DatabaseService

logger = logging.getLogger("eakap.analytics.sql_executor")


class SQLExecutor:
    """Execute validated SQL through DatabaseService only."""

    def __init__(self, database_service: type[DatabaseService] = DatabaseService) -> None:
        self.database_service = database_service

    def execute(self, sql: str) -> SQLExecutionResult:
        """Execute SQL and return structured rows, columns, and latency."""
        start = time.perf_counter()
        try:
            rows = self.database_service.execute_query(sql)
            execution_time_ms = (time.perf_counter() - start) * 1_000
            columns = list(rows[0].keys()) if rows else []
            logger.info("Analytics SQL executed | rows=%s", len(rows))
            return SQLExecutionResult(
                rows=rows,
                columns=columns,
                row_count=len(rows),
                execution_time_ms=execution_time_ms,
            )
        except Exception as exc:
            raise SQLExecutionError(
                message="Failed to execute validated analytics SQL.",
                original_exception=exc,
            )
