"""Domain model for an enterprise RAG query."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class RAGQuery(BaseModel):
    """Validated input contract for the query processing pipeline."""

    query_text: str = Field(..., min_length=1)
    filters: Optional[Dict[str, Any]] = None
    top_k: int = Field(default=5, ge=1, le=100)
    similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    session_id: Optional[str] = None
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("query_text")
    @classmethod
    def query_text_must_not_be_blank(cls, value: str) -> str:
        """Reject empty or whitespace-only queries."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("query_text must be a non-empty string.")
        return stripped
