from typing import Iterator, List, Tuple

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.rag.context.builder import ContextBuilder
from src.rag.formatting.formatter import ResponseFormatter
from src.rag.llm.base import BaseLLMProvider
from src.rag.llm.mock import MockLLMProvider
from src.rag.models import RAGQuery, RAGResponse, RetrievedChunk
from src.rag.models.telemetry import (
    QueryTelemetry,
    TELEMETRY_STATUS_INSUFFICIENT,
    TELEMETRY_STATUS_SUCCESS,
)
from src.rag.pipeline.query_engine import QueryEngine
from src.rag.prompts.manager import INSUFFICIENT_CONTEXT_SENTINEL, PromptManager
from src.rag.retrieval.retriever import VectorRetriever


class FakeEmbeddingService:
    provider = type("FakeEmbeddingProvider", (), {})()

    def embed_query(self, text: str) -> List[float]:
        return [0.1, 0.2, 0.3]


class FakeChromaService:
    def similarity_search(self, collection_name, query_embedding, n_results, where_filter=None):
        return [
            {
                "document": "High confidence prior authorization policy.",
                "distance": 0.05,
                "metadata": {
                    "filename": "policy.md",
                    "sha256": "abc",
                    "chunk_index": 0,
                },
            },
            {
                "document": "Low confidence unrelated content.",
                "distance": 0.80,
                "metadata": {
                    "filename": "notes.md",
                    "sha256": "def",
                    "chunk_index": 1,
                },
            },
        ][:n_results]


class StaticRetriever:
    def __init__(self, chunks: List[RetrievedChunk]) -> None:
        self.chunks = chunks

    def retrieve(self, query: RAGQuery) -> List[RetrievedChunk]:
        return self.chunks


class CapturingLLMProvider(BaseLLMProvider):
    def __init__(self, response: str = "Prior authorization is required [1].") -> None:
        self.response = response
        self.last_prompt = ""

    @property
    def provider_name(self) -> str:
        return "capturing"

    @property
    def model_name(self) -> str:
        return "capturing-v1"

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> Tuple[str, int, int]:
        self.last_prompt = prompt
        return self.response, 42, 7

    def stream_generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> Iterator[str]:
        yield from ["Prior ", "authorization"]


def make_chunk(content: str, score: float, index: int = 0) -> RetrievedChunk:
    return RetrievedChunk(
        content=content,
        similarity_score=score,
        source_filename="policy.md",
        source_document_hash="hash",
        chunk_index=index,
        metadata={"chunk_index": index},
    )


def test_domain_model_validation():
    query = RAGQuery(query_text="  What is required?  ", top_k=3, similarity_threshold=0.2)
    chunk = make_chunk("Evidence", 0.9)

    assert query.query_text == "What is required?"
    assert query.top_k == 3
    assert chunk.citation == "[policy.md | chunk 0]"

    with pytest.raises(PydanticValidationError):
        RAGQuery(query_text="   ")
    with pytest.raises(PydanticValidationError):
        RetrievedChunk(content="", similarity_score=1.2, source_filename="x", chunk_index=0)


def test_retriever_similarity_score_filtering():
    retriever = VectorRetriever(
        embedding_service=FakeEmbeddingService(),
        chroma_service=FakeChromaService(),
        collection_name="test_collection",
    )

    chunks = retriever.retrieve(
        RAGQuery(query_text="prior authorization", top_k=2, similarity_threshold=0.5)
    )

    assert len(chunks) == 1
    assert chunks[0].similarity_score == pytest.approx(0.95)
    assert chunks[0].source_filename == "policy.md"


def test_context_builder_duplicate_removal_and_token_limit_clipping():
    chunks = [
        make_chunk("Duplicate policy text.", 0.7, 0),
        make_chunk("Duplicate policy text.", 0.9, 1),
        make_chunk("A long second policy text that can be clipped by the token budget.", 0.8, 2),
    ]
    builder = ContextBuilder(max_context_tokens=35)

    context, citations = builder.build(chunks)

    assert context.count("Duplicate policy text.") == 1
    assert "[1]" in context
    assert len(context) <= 35 * 4
    assert citations[0].startswith("[1]")


def test_prompt_manager_version_lookup():
    manager = PromptManager()
    template = manager.get_template("clinical_qa", "1.0")
    rendered = template.render(context="Evidence [1]", query="Question?")

    assert template.version == "1.0"
    assert "Answer ONLY from the provided context" in rendered
    assert INSUFFICIENT_CONTEXT_SENTINEL in rendered


def test_mocked_llm_execution_and_stream_generation():
    provider = MockLLMProvider(fixed_response="Grounded answer [1].")

    text, prompt_tokens, completion_tokens = provider.generate("CONTEXT:\nEvidence\n\nQUESTION:\nQ")
    stream_text = "".join(provider.stream_generate("CONTEXT:\nEvidence\n\nQUESTION:\nQ"))

    assert text == "Grounded answer [1]."
    assert prompt_tokens > 0
    assert completion_tokens > 0
    assert "Grounded answer" in stream_text


def test_response_formatter_output_verification():
    formatter = ResponseFormatter()
    telemetry = QueryTelemetry(
        query_id="q1",
        embedding_provider="mock-embedding",
        llm_provider="mock",
        model_name="mock-v1",
        prompt_tokens=10,
        completion_tokens=5,
    )
    chunk = make_chunk("Evidence", 0.9)

    response = formatter.format("Answer [1].", ["[1] [policy.md | chunk 0]"], [chunk], telemetry)

    assert isinstance(response, RAGResponse)
    assert response.answer == "Answer [1]."
    assert response.telemetry.status == TELEMETRY_STATUS_SUCCESS
    assert response.telemetry.total_tokens == 15
    assert response.source_documents == ["policy.md"]


def test_end_to_end_query_engine_orchestration():
    chunks = [make_chunk("Prior authorization is required for this service.", 0.92)]
    llm = CapturingLLMProvider()
    engine = QueryEngine(
        retriever=StaticRetriever(chunks),
        llm_provider=llm,
        embedding_provider_name="fake",
    )

    response = engine.execute(RAGQuery(query_text="Is prior authorization required?"))

    assert response.answer == "Prior authorization is required [1]."
    assert response.citations == ["[1] [policy.md | chunk 0]"]
    assert response.execution_metadata["prompt_name"] == "clinical_qa"
    assert response.telemetry.llm_provider == "capturing"
    assert "Prior authorization is required for this service." in llm.last_prompt


def test_query_engine_graceful_fallback_for_insufficient_context():
    engine = QueryEngine(
        retriever=StaticRetriever([]),
        llm_provider=MockLLMProvider(),
        embedding_provider_name="fake",
    )

    response = engine.execute(RAGQuery(query_text="What is the formulary rule?"))

    assert response.answer == INSUFFICIENT_CONTEXT_SENTINEL
    assert response.telemetry.status == TELEMETRY_STATUS_INSUFFICIENT
    assert response.retrieved_chunks == []
