"""Telemetry model for conversation memory operations."""

from pydantic import BaseModel, Field


class MemoryTelemetry(BaseModel):
    """Metrics emitted by memory retrieval, formatting, and trimming."""

    session_id: str
    total_turns: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    trimmed_turns: int = Field(default=0, ge=0)
    retrieval_time_ms: float = Field(default=0.0, ge=0.0)
    formatting_time_ms: float = Field(default=0.0, ge=0.0)
