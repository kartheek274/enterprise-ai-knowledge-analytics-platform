"""Response model returned by the enterprise RAG query engine."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from src.rag.models.retrieved_chunk import RetrievedChunk
from src.rag.models.telemetry import QueryTelemetry


class RAGResponse(BaseModel):
    """Complete answer payload with citations, provenance, and telemetry."""

    answer: str
    citations: List[str] = Field(default_factory=list)
    retrieved_chunks: List[RetrievedChunk] = Field(default_factory=list)
    telemetry: QueryTelemetry
    execution_metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_grounded(self) -> bool:
        """Return true when retrieved evidence was available."""
        return bool(self.retrieved_chunks)

    @property
    def source_documents(self) -> List[str]:
        """Return unique source filenames referenced by this response."""
        seen: List[str] = []
        for chunk in self.retrieved_chunks:
            if chunk.source_filename not in seen:
                seen.append(chunk.source_filename)
        return seen
