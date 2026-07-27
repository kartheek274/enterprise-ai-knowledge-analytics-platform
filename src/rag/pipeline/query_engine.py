"""Thin RAG query orchestration pipeline."""

import time
from typing import Optional

from src.common.errors.exceptions import EAKAPBaseException
from src.governance.service import GovernanceService
from src.rag.context.builder import ContextBuilder
from src.rag.embeddings.embedding_service import EmbeddingService
from src.rag.formatting.formatter import ResponseFormatter
from src.rag.llm.base import BaseLLMProvider
from src.rag.llm.llm_provider import get_llm_provider
from src.rag.models.query import RAGQuery
from src.rag.models.rag_response import RAGResponse
from src.rag.models.telemetry import QueryTelemetry, TELEMETRY_STATUS_ERROR
from src.rag.memory.manager import SessionMemoryManager
from src.rag.prompts.manager import PromptManager
from src.rag.retrieval.base import BaseRetriever
from src.rag.retrieval.bm25_retriever import BM25Retriever
from src.rag.retrieval.hybrid_retriever import HybridRetriever
from src.rag.retrieval.reranker import BaseReranker, CrossEncoderReranker
from src.rag.retrieval.retriever import VectorRetriever
from src.rag.vector_store.chroma_service import ChromaService


class QueryEngine:
    """Coordinate retrieval, context building, prompting, generation, and formatting."""

    def __init__(
        self,
        retriever: Optional[BaseRetriever] = None,
        context_builder: Optional[ContextBuilder] = None,
        prompt_manager: Optional[PromptManager] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        reranker: Optional[BaseReranker] = None,
        memory_manager: Optional[SessionMemoryManager] = None,
        governance_service: Optional[GovernanceService] = None,
        response_formatter: Optional[ResponseFormatter] = None,
        collection_name: str = "healthcare_knowledge",
        embedding_provider_name: Optional[str] = None,
    ) -> None:
        self.llm_provider = llm_provider or get_llm_provider()
        self.context_builder = context_builder or ContextBuilder()
        self.prompt_manager = prompt_manager or PromptManager()
        self.response_formatter = response_formatter or ResponseFormatter()
        self.memory_manager = memory_manager
        self.governance_service = governance_service or GovernanceService()
        self.collection_name = collection_name
        self.embedding_provider_name = embedding_provider_name

        if retriever is None:
            embedding_service = EmbeddingService()
            vector_retriever = VectorRetriever(
                embedding_service=embedding_service,
                chroma_service=ChromaService(),
                collection_name=collection_name,
            )
            self.retriever: BaseRetriever = HybridRetriever(
                vector_retriever=vector_retriever,
                bm25_retriever=BM25Retriever(),
                reranker=reranker or CrossEncoderReranker(),
            )
            self.embedding_provider_name = (
                embedding_provider_name or embedding_service.provider.__class__.__name__
            )
        else:
            self.retriever = retriever
            self.embedding_provider_name = embedding_provider_name or "injected"

    def execute(
        self,
        query: RAGQuery,
        prompt_name: str = "clinical_qa",
        prompt_version: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> RAGResponse:
        """Execute the full RAG pipeline for a validated query."""
        total_start = time.perf_counter()
        self.governance_service.validate_input(query.query_text)

        conversation_history = ""
        if query.session_id and self.memory_manager is not None:
            conversation_history = self.memory_manager.get_formatted_history(query.session_id)

        retrieval_start = time.perf_counter()
        chunks = self.retriever.retrieve(query)
        retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1_000

        context, citations = self.context_builder.build(
            chunks,
            conversation_history=conversation_history,
        )
        template = self.prompt_manager.get_template(name=prompt_name, version=prompt_version)
        prompt = template.render(context=context, query=query.query_text)

        generation_start = time.perf_counter()
        try:
            llm_text, prompt_tokens, completion_tokens = self.llm_provider.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except EAKAPBaseException:
            raise
        generation_time_ms = (time.perf_counter() - generation_start) * 1_000
        sanitized_output = self.governance_service.sanitize_output(llm_text)
        safe_llm_text = sanitized_output.sanitized_text or llm_text

        telemetry = QueryTelemetry(
            query_id=query.request_id,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
            total_time_ms=(time.perf_counter() - total_start) * 1_000,
            embedding_provider=self.embedding_provider_name or "unknown",
            llm_provider=self.llm_provider.provider_name,
            model_name=self.llm_provider.model_name,
            retrieved_chunk_count=len(chunks),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

        response = self.response_formatter.format(
            llm_text=safe_llm_text,
            citations=citations,
            retrieved_chunks=chunks,
            telemetry=telemetry,
            execution_metadata={
                "collection_name": self.collection_name,
                "prompt_name": template.name,
                "prompt_version": template.version,
                "session_id": query.session_id,
                "governance": self.governance_service.last_telemetry.model_dump(),
            },
        )
        if query.session_id and self.memory_manager is not None:
            self.memory_manager.add_turn(
                session_id=query.session_id,
                role="user",
                content=query.query_text,
            )
            self.memory_manager.add_turn(
                session_id=query.session_id,
                role="assistant",
                content=response.answer,
            )
        return response

    def execute_with_error_response(self, query: RAGQuery, **kwargs: object) -> RAGResponse:
        """Execute and convert platform exceptions into structured error responses."""
        try:
            return self.execute(query, **kwargs)
        except EAKAPBaseException as exc:
            telemetry = QueryTelemetry(
                query_id=query.request_id,
                embedding_provider=self.embedding_provider_name or "unknown",
                llm_provider=self.llm_provider.provider_name,
                model_name=self.llm_provider.model_name,
                status=TELEMETRY_STATUS_ERROR,
                error_message=str(exc),
            )
            return RAGResponse(
                answer="INSUFFICIENT_CONTEXT",
                citations=[],
                retrieved_chunks=[],
                telemetry=telemetry,
                execution_metadata={"error": str(exc)},
            )
