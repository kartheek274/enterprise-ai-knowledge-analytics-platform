"""Analytics response formatter."""

from src.analytics.models import AnalyticsResponse, AnalyticsTelemetry, SQLExecutionResult


class ResultFormatter:
    """Assemble the final AnalyticsResponse without executing SQL or calling LLMs."""

    def format(
        self,
        question: str,
        generated_sql: str,
        execution_result: SQLExecutionResult,
        summary: str,
        telemetry: AnalyticsTelemetry,
    ) -> AnalyticsResponse:
        """Return a standardized analytics response."""
        telemetry.row_count = execution_result.row_count
        telemetry.sql_execution_ms = execution_result.execution_time_ms
        return AnalyticsResponse(
            question=question,
            generated_sql=generated_sql,
            execution_result=execution_result,
            summary=summary,
            telemetry=telemetry,
        )
