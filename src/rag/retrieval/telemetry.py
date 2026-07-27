"""Telemetry model for advanced retrieval diagnostics."""

from pydantic import BaseModel, Field


class RetrievalTelemetry(BaseModel):
    """Timing and candidate metrics emitted by hybrid retrieval."""

    vector_retrieval_time_ms: float = Field(default=0.0, ge=0.0)
    bm25_retrieval_time_ms: float = Field(default=0.0, ge=0.0)
    fusion_time_ms: float = Field(default=0.0, ge=0.0)
    reranking_time_ms: float = Field(default=0.0, ge=0.0)
    retrieved_candidate_count: int = Field(default=0, ge=0)
    reranked_candidate_count: int = Field(default=0, ge=0)
    reranker_name: str = "none"
