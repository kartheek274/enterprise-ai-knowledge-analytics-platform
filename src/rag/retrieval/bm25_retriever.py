"""In-memory BM25 sparse retriever."""

import logging
import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Optional

from src.rag.models.query import RAGQuery
from src.rag.models.retrieved_chunk import RetrievedChunk
from src.rag.retrieval.base import BaseRetriever

logger = logging.getLogger("eakap.rag.bm25_retriever")


class BM25Retriever(BaseRetriever):
    """Retrieve chunks using sparse keyword matching with BM25 scoring."""

    def __init__(
        self,
        chunks: Optional[Iterable[RetrievedChunk]] = None,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b
        self._chunks: List[RetrievedChunk] = []
        self._term_frequencies: List[Counter[str]] = []
        self._document_frequencies: Counter[str] = Counter()
        self._document_lengths: List[int] = []
        self._average_document_length = 0.0
        if chunks:
            self.build_index(chunks)

    def build_index(self, chunks: Iterable[RetrievedChunk]) -> None:
        """Build or replace the in-memory BM25 index."""
        self._chunks = list(chunks)
        self._term_frequencies = []
        self._document_frequencies = Counter()
        self._document_lengths = []

        for chunk in self._chunks:
            terms = self._tokenize(chunk.content)
            frequencies = Counter(terms)
            self._term_frequencies.append(frequencies)
            self._document_lengths.append(len(terms))
            self._document_frequencies.update(set(terms))

        total_length = sum(self._document_lengths)
        self._average_document_length = (
            total_length / len(self._document_lengths)
            if self._document_lengths
            else 0.0
        )
        logger.info("BM25 index built | chunks=%s", len(self._chunks))

    def retrieve(self, query: RAGQuery) -> List[RetrievedChunk]:
        """Return sparse keyword matches ordered by BM25 score descending."""
        if not self._chunks:
            return []

        query_terms = self._tokenize(query.query_text)
        if not query_terms:
            return []

        scored_chunks = []
        for index, chunk in enumerate(self._chunks):
            score = self._score(query_terms, index)
            if score <= 0.0:
                continue
            scored_chunks.append((score, chunk))

        if not scored_chunks:
            return []

        max_score = max(score for score, _ in scored_chunks) or 1.0
        ranked = sorted(
            scored_chunks,
            key=lambda item: (-item[0], self._stable_key(item[1])),
        )[: query.top_k]

        results: List[RetrievedChunk] = []
        for score, chunk in ranked:
            results.append(
                chunk.model_copy(
                    update={
                        "similarity_score": min(1.0, score / max_score),
                        "metadata": {
                            **chunk.metadata,
                            "retrieval_strategy": "bm25",
                            "bm25_score": score,
                        },
                    }
                )
            )
        return results

    def is_initialized(self) -> bool:
        """Return true when an index is available."""
        return bool(self._chunks)

    def _score(self, query_terms: List[str], document_index: int) -> float:
        score = 0.0
        frequencies = self._term_frequencies[document_index]
        document_length = self._document_lengths[document_index]
        corpus_size = len(self._chunks)
        for term in query_terms:
            term_frequency = frequencies.get(term, 0)
            if term_frequency == 0:
                continue
            document_frequency = self._document_frequencies.get(term, 0)
            idf = math.log(1 + (corpus_size - document_frequency + 0.5) / (document_frequency + 0.5))
            denominator = term_frequency + self.k1 * (
                1 - self.b + self.b * document_length / max(self._average_document_length, 1.0)
            )
            score += idf * (term_frequency * (self.k1 + 1)) / denominator
        return score

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"[a-zA-Z0-9_]+", text.lower())

    @staticmethod
    def _stable_key(chunk: RetrievedChunk) -> str:
        return (
            chunk.source_document_hash
            or f"{chunk.source_filename}:{chunk.chunk_index}:{chunk.content[:32]}"
        )
