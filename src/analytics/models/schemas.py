"""Pydantic domain models for conversational analytics."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class SQLQueryRequest(BaseModel):
    """Validated natural-language analytics request."""

    question: str = Field(..., min_length=1)
    user_id: Optional[str] = None
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        """Normalize and reject empty questions."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must be a non-empty string.")
        return stripped


class SQLValidationResult(BaseModel):
    """Outcome of enterprise SQL safety validation."""

    is_valid: bool
    sanitized_sql: Optional[str] = None
    error_message: Optional[str] = None


class SQLExecutionResult(BaseModel):
    """Structured result returned by SQL execution."""

    rows: List[Dict[str, Any]] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    row_count: int = Field(default=0, ge=0)
    execution_time_ms: float = Field(default=0.0, ge=0.0)


class AnalyticsTelemetry(BaseModel):
    """Timing and outcome metrics for conversational BI execution."""

    sql_generation_ms: float = Field(default=0.0, ge=0.0)
    sql_validation_ms: float = Field(default=0.0, ge=0.0)
    sql_execution_ms: float = Field(default=0.0, ge=0.0)
    summary_generation_ms: float = Field(default=0.0, ge=0.0)
    total_execution_ms: float = Field(default=0.0, ge=0.0)
    model_name: str = "unknown"
    row_count: int = Field(default=0, ge=0)
    status: str = "SUCCESS"


class AnalyticsResponse(BaseModel):
    """Final response returned by the conversational BI engine."""

    question: str
    generated_sql: str
    execution_result: SQLExecutionResult
    summary: str
    telemetry: AnalyticsTelemetry
