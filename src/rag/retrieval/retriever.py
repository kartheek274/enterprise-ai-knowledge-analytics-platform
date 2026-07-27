"""Vector retrieval service for RAG grounding evidence."""

import logging
from typing import Any, Dict, List, Optional

from src.common.errors.exceptions import RetrievalError
from src.rag.embeddings.embedding_service import EmbeddingService
from src.rag.models.query import RAGQuery
from src.rag.models.retrieved_chunk import RetrievedChunk
from src.rag.retrieval.base import BaseRetriever
from src.rag.vector_store.chroma_service import ChromaService

logger = logging.getLogger("eakap.rag.retriever")


class VectorRetriever(BaseRetriever):
    """Retrieve top-K chunks from ChromaDB and map them to domain objects."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        chroma_service: ChromaService,
        collection_name: str = "healthcare_knowledge",
    ) -> None:
        self.embedding_service = embedding_service
        self.chroma_service = chroma_service
        self.collection_name = collection_name

    def retrieve(self, query: RAGQuery) -> List[RetrievedChunk]:
        """Run vector search and filter results by minimum similarity score."""
        try:
            query_embedding = self.embedding_service.embed_query(query.query_text)
            raw_results = self.chroma_service.similarity_search(
                collection_name=self.collection_name,
                query_embedding=query_embedding,
                n_results=query.top_k,
                where_filter=query.filters or None,
            )

            chunks = [
                chunk
                for chunk in (self._to_retrieved_chunk(result) for result in raw_results)
                if chunk.similarity_score >= query.similarity_threshold
            ]
            chunks.sort(key=lambda chunk: chunk.similarity_score, reverse=True)
            logger.info(
                "Vector retrieval completed | query_id=%s | raw=%s | retained=%s",
                query.request_id,
                len(raw_results),
                len(chunks),
            )
            return chunks
        except RetrievalError:
            raise
        except Exception as exc:
            raise RetrievalError(
                message=f"Vector retrieval failed for query_id={query.request_id}.",
                original_exception=exc,
            )

    @staticmethod
    def _to_retrieved_chunk(result: Dict[str, Any]) -> RetrievedChunk:
        """Map a ChromaService result dictionary into a RetrievedChunk."""
        metadata = result.get("metadata") or {}
        similarity_score = VectorRetriever._extract_similarity_score(result)
        return RetrievedChunk(
            content=result.get("document") or result.get("content") or "",
            similarity_score=similarity_score,
            source_filename=(
                metadata.get("source_filename")
                or metadata.get("filename")
                or metadata.get("source")
                or "unknown"
            ),
            source_document_hash=(
                metadata.get("source_document_hash")
                or metadata.get("document_hash")
                or metadata.get("sha256")
            ),
            chunk_index=int(metadata.get("chunk_index", result.get("chunk_index", 0)) or 0),
            metadata=metadata,
        )

    @staticmethod
    def _extract_similarity_score(result: Dict[str, Any]) -> float:
        """Return a normalized similarity score from a raw vector-store result."""
        if "similarity_score" in result:
            return max(0.0, min(1.0, float(result["similarity_score"])))
        if "score" in result:
            return max(0.0, min(1.0, float(result["score"])))
        distance = float(result.get("distance", 0.0) or 0.0)
        return max(0.0, min(1.0, 1.0 - distance))


Retriever = VectorRetriever
