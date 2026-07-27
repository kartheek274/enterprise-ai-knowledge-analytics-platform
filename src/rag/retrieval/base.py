"""Retrieval abstraction for RAG grounding strategies."""

from abc import ABC, abstractmethod
from typing import List

from src.rag.models.query import RAGQuery
from src.rag.models.retrieved_chunk import RetrievedChunk


class BaseRetriever(ABC):
    """Common contract implemented by all retrieval strategies."""

    @abstractmethod
    def retrieve(self, query: RAGQuery) -> List[RetrievedChunk]:
        """Return relevant chunks for a validated RAG query."""
