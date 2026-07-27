"""Thin conversational BI pipeline orchestrator."""

import logging
import time
from typing import Optional

from src.analytics.exceptions import AnalyticsExecutionError, SQLValidationError
from src.analytics.models import AnalyticsResponse, AnalyticsTelemetry, SQLQueryRequest
from src.analytics.result_formatter import ResultFormatter
from src.analytics.schema_inspector import SchemaInspector
from src.analytics.sql_executor import SQLExecutor
from src.analytics.sql_generator import SQLGenerator
from src.analytics.sql_validator import SQLValidator
from src.analytics.summary_generator import SummaryGenerator
from src.governance.service import GovernanceService
from src.rag.llm.base import BaseLLMProvider
from src.rag.llm.llm_provider import get_llm_provider

logger = logging.getLogger("eakap.analytics.bi_engine")


class ConversationalBIEngine:
    """Coordinate schema inspection, SQL generation, validation, execution, and summary."""

    def __init__(
        self,
        schema_inspector: Optional[SchemaInspector] = None,
        sql_generator: Optional[SQLGenerator] = None,
        sql_validator: Optional[SQLValidator] = None,
        sql_executor: Optional[SQLExecutor] = None,
        summary_generator: Optional[SummaryGenerator] = None,
        result_formatter: Optional[ResultFormatter] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        governance_service: Optional[GovernanceService] = None,
    ) -> None:
        provider = llm_provider or get_llm_provider()
        self.schema_inspector = schema_inspector or SchemaInspector()
        self.sql_generator = sql_generator or SQLGenerator(provider)
        self.sql_validator = sql_validator or SQLValidator(self.schema_inspector)
        self.sql_executor = sql_executor or SQLExecutor()
        self.summary_generator = summary_generator or SummaryGenerator(provider)
        self.result_formatter = result_formatter or ResultFormatter()
        self.llm_provider = provider
        self.governance_service = governance_service or GovernanceService()

    def execute(self, request: SQLQueryRequest) -> AnalyticsResponse:
        """Execute the conversational BI pipeline."""
        total_start = time.perf_counter()
        telemetry = AnalyticsTelemetry(model_name=self.llm_provider.model_name)
        try:
            self.governance_service.validate_input(request.question)
            schema_context = self.schema_inspector.get_schema_context()

            start = time.perf_counter()
            candidate_sql = self.sql_generator.generate_sql(
                question=request.question,
                schema_context=schema_context,
            )
            telemetry.sql_generation_ms = (time.perf_counter() - start) * 1_000

            start = time.perf_counter()
            validation = self.sql_validator.validate(candidate_sql)
            telemetry.sql_validation_ms = (time.perf_counter() - start) * 1_000
            if not validation.is_valid or not validation.sanitized_sql:
                raise SQLValidationError(message=validation.error_message or "SQL validation failed.")

            execution_result = self.sql_executor.execute(validation.sanitized_sql)

            start = time.perf_counter()
            summary = self.summary_generator.generate_summary(
                question=request.question,
                execution_result=execution_result,
            )
            sanitized_summary = self.governance_service.sanitize_output(summary)
            safe_summary = sanitized_summary.sanitized_text or summary
            telemetry.summary_generation_ms = (time.perf_counter() - start) * 1_000
            telemetry.total_execution_ms = (time.perf_counter() - total_start) * 1_000
            telemetry.status = "SUCCESS"

            return self.result_formatter.format(
                question=request.question,
                generated_sql=validation.sanitized_sql,
                execution_result=execution_result,
                summary=safe_summary,
                telemetry=telemetry,
            )
        except Exception as exc:
            telemetry.total_execution_ms = (time.perf_counter() - total_start) * 1_000
            telemetry.status = "ERROR"
            logger.error("Conversational BI execution failed: %s", str(exc))
            if isinstance(exc, AnalyticsExecutionError):
                raise
            raise AnalyticsExecutionError(
                message="Conversational BI pipeline failed.",
                original_exception=exc,
            )
