"""Reranker abstractions and implementations for retrieval candidates."""

import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional

from src.rag.models.query import RAGQuery
from src.rag.models.retrieved_chunk import RetrievedChunk

logger = logging.getLogger("eakap.rag.reranker")


class BaseReranker(ABC):
    """Contract for candidate reranking implementations."""

    @abstractmethod
    def rerank(self, query: RAGQuery, chunks: List[RetrievedChunk], top_k: int) -> List[RetrievedChunk]:
        """Return reranked candidate chunks."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return reranker identifier."""

    @property
    @abstractmethod
    def available(self) -> bool:
        """Return true when the reranker can actively score candidates."""


class PassThroughReranker(BaseReranker):
    """Fallback reranker that preserves existing candidate ordering."""

    @property
    def name(self) -> str:
        return "pass_through"

    @property
    def available(self) -> bool:
        return True

    def rerank(self, query: RAGQuery, chunks: List[RetrievedChunk], top_k: int) -> List[RetrievedChunk]:
        return chunks[:top_k]


class CrossEncoderReranker(BaseReranker):
    """
    Cross-encoder reranker with graceful fallback.

    If a sentence-transformers CrossEncoder cannot be initialized, reranking
    falls back to deterministic lexical overlap and preserves original ordering
    for equal scores. This avoids downloads and external calls during tests.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        model: Optional[object] = None,
        enable_model_loading: bool = False,
    ) -> None:
        self.model_name = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self._model = model
        self._available = model is not None
        if self._model is None and enable_model_loading:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name)
                self._available = True
            except Exception as exc:
                logger.warning("CrossEncoder unavailable; using lexical fallback: %s", str(exc))
                self._available = False

    @property
    def name(self) -> str:
        return "cross_encoder" if self.available else "cross_encoder_fallback"

    @property
    def available(self) -> bool:
        return self._available

    def rerank(self, query: RAGQuery, chunks: List[RetrievedChunk], top_k: int) -> List[RetrievedChunk]:
        if not chunks:
            return []
        try:
            scores = self._score(query, chunks)
            indexed = list(enumerate(zip(scores, chunks)))
            indexed.sort(
                key=lambda item: (
                    -item[1][0],
                    item[0],
                    self._stable_key(item[1][1]),
                )
            )
            reranked = []
            for _, (score, chunk) in indexed[:top_k]:
                reranked.append(
                    chunk.model_copy(
                        update={
                            "metadata": {
                                **chunk.metadata,
                                "reranker": self.name,
                                "rerank_score": score,
                            }
                        }
                    )
                )
            return reranked
        except Exception as exc:
            logger.warning("Reranker failed; preserving original order: %s", str(exc))
            return chunks[:top_k]

    def _score(self, query: RAGQuery, chunks: List[RetrievedChunk]) -> List[float]:
        if self._model is not None:
            pairs = [(query.query_text, chunk.content) for chunk in chunks]
            raw_scores = self._model.predict(pairs)
            return [float(score) for score in raw_scores]
        query_terms = set(self._tokenize(query.query_text))
        scores = []
        for chunk in chunks:
            chunk_terms = set(self._tokenize(chunk.content))
            overlap = len(query_terms & chunk_terms)
            scores.append(float(overlap))
        return scores

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9_]+", text.lower())

    @staticmethod
    def _stable_key(chunk: RetrievedChunk) -> str:
        return (
            chunk.source_document_hash
            or f"{chunk.source_filename}:{chunk.chunk_index}:{chunk.content[:32]}"
        )
