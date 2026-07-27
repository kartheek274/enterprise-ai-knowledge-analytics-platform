"""Domain model for a knowledge chunk retrieved from vector search."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class RetrievedChunk(BaseModel):
    """Validated representation of a retrieved document fragment."""

    content: str = Field(..., min_length=1)
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    source_filename: str = Field(default="unknown")
    source_document_hash: Optional[str] = None
    chunk_index: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        """Reject empty or whitespace-only chunks."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("content must be a non-empty string.")
        return stripped

    @property
    def citation(self) -> str:
        """Return a stable, human-readable source reference for this chunk."""
        return f"[{self.source_filename} | chunk {self.chunk_index}]"
