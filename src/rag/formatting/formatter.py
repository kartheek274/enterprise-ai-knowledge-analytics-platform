"""Assemble final RAG responses and telemetry."""

from typing import Any, Dict, List, Optional

from src.rag.models.rag_response import RAGResponse
from src.rag.models.retrieved_chunk import RetrievedChunk
from src.rag.models.telemetry import (
    QueryTelemetry,
    TELEMETRY_STATUS_INSUFFICIENT,
    TELEMETRY_STATUS_SUCCESS,
)
from src.rag.prompts.manager import INSUFFICIENT_CONTEXT_SENTINEL


class ResponseFormatter:
    """Build a typed RAGResponse from query engine execution artifacts."""

    @staticmethod
    def format(
        llm_text: str,
        citations: List[str],
        retrieved_chunks: List[RetrievedChunk],
        telemetry: QueryTelemetry,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> RAGResponse:
        """Return a normalized response and updated telemetry status."""
        answer = llm_text.strip()
        if answer == INSUFFICIENT_CONTEXT_SENTINEL or INSUFFICIENT_CONTEXT_SENTINEL in answer:
            answer = INSUFFICIENT_CONTEXT_SENTINEL
            telemetry.status = TELEMETRY_STATUS_INSUFFICIENT
        else:
            telemetry.status = telemetry.status or TELEMETRY_STATUS_SUCCESS

        telemetry.retrieved_chunk_count = len(retrieved_chunks)
        telemetry.total_tokens = telemetry.prompt_tokens + telemetry.completion_tokens
        return RAGResponse(
            answer=answer,
            citations=citations,
            retrieved_chunks=retrieved_chunks,
            telemetry=telemetry,
            execution_metadata=execution_metadata or {},
        )

    @staticmethod
    def extract_citations(retrieved_chunks: List[RetrievedChunk]) -> List[str]:
        """Return deduplicated source citations from retrieved chunks."""
        citations: List[str] = []
        for chunk in retrieved_chunks:
            citation = chunk.citation
            if citation not in citations:
                citations.append(citation)
        return citations
