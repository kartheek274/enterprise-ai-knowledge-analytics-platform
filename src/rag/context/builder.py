"""Build grounded context blocks from retrieved chunks."""

import logging
from typing import List, Optional, Tuple

from src.rag.models.retrieved_chunk import RetrievedChunk

logger = logging.getLogger("eakap.rag.context_builder")

_CHARS_PER_TOKEN = 4


class ContextBuilder:
    """Construct citation-tagged context within a configurable token budget."""

    def __init__(self, max_context_tokens: int = 2_000) -> None:
        if max_context_tokens < 1:
            raise ValueError("max_context_tokens must be at least 1.")
        self.max_context_tokens = max_context_tokens
        self._max_chars = max_context_tokens * _CHARS_PER_TOKEN

    def build(
        self,
        chunks: List[RetrievedChunk],
        conversation_history: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        """Return formatted context text and ordered citation references."""
        history = conversation_history.strip() if conversation_history else ""

        unique_chunks = self._deduplicate(chunks)
        context_blocks: List[str] = []
        citations: List[str] = []
        used_chars = 0

        if history:
            history_block = f"CONVERSATION HISTORY:\n{history}"
            if len(history_block) > self._max_chars:
                history_block = history_block[: max(0, self._max_chars - 3)].rstrip() + "..."
            context_blocks.append(history_block)
            used_chars += len(history_block)

        for index, chunk in enumerate(unique_chunks, start=1):
            citation_tag = f"[{index}]"
            block = (
                f"{citation_tag}\n"
                f"Source: {chunk.source_filename}\n"
                f"Document Hash: {chunk.source_document_hash or 'unknown'}\n"
                f"Chunk: {chunk.chunk_index}\n"
                f"Content: {chunk.content.strip()}"
            )
            separator_chars = 2 if context_blocks else 0
            remaining = self._max_chars - used_chars - separator_chars
            if remaining <= 0:
                break
            if len(block) > remaining:
                if remaining < 80:
                    break
                block = block[: max(0, remaining - 3)].rstrip() + "..."

            context_blocks.append(block)
            citations.append(f"{citation_tag} {chunk.citation}")
            used_chars += len(block) + separator_chars

        logger.debug(
            "Context built | input_chunks=%s | retained_chunks=%s | chars=%s",
            len(chunks),
            len(context_blocks),
            used_chars,
        )
        return "\n\n".join(context_blocks), citations

    def build_context(
        self,
        chunks: List[RetrievedChunk],
        conversation_history: Optional[str] = None,
    ) -> str:
        """Return only the formatted context string for callers that do not need citations."""
        context, _ = self.build(chunks, conversation_history=conversation_history)
        return context

    @staticmethod
    def _deduplicate(chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """Remove duplicate content and return chunks ordered by similarity descending."""
        sorted_chunks = sorted(chunks, key=lambda chunk: chunk.similarity_score, reverse=True)
        seen_content = set()
        unique_chunks: List[RetrievedChunk] = []
        for chunk in sorted_chunks:
            normalized = " ".join(chunk.content.split()).lower()
            if normalized in seen_content:
                continue
            seen_content.add(normalized)
            unique_chunks.append(chunk)
        return unique_chunks
