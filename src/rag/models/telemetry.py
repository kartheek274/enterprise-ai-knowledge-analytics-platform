"""Telemetry model for a single RAG query execution."""

from typing import Optional

from pydantic import BaseModel, Field


TELEMETRY_STATUS_SUCCESS = "SUCCESS"
TELEMETRY_STATUS_INSUFFICIENT = "INSUFFICIENT_CONTEXT"
TELEMETRY_STATUS_ERROR = "ERROR"


class QueryTelemetry(BaseModel):
    """Timing, provider, token, and outcome metrics for RAG observability."""

    query_id: str
    retrieval_time_ms: float = Field(default=0.0, ge=0.0)
    generation_time_ms: float = Field(default=0.0, ge=0.0)
    total_time_ms: float = Field(default=0.0, ge=0.0)
    embedding_provider: str
    llm_provider: str
    model_name: str
    retrieved_chunk_count: int = Field(default=0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    status: str = TELEMETRY_STATUS_SUCCESS
    error_message: Optional[str] = None

    @property
    def context_assembly_time_ms(self) -> float:
        """Return non-retrieval and non-generation elapsed time."""
        return max(
            0.0,
            self.total_time_ms - self.retrieval_time_ms - self.generation_time_ms,
        )
