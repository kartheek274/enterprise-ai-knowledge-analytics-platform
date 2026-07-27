from typing import List

import pytest

from src.common.config.settings import get_settings
from src.rag.llm.mock import MockLLMProvider
from src.rag.models import RAGQuery, RetrievedChunk
from src.rag.pipeline.query_engine import QueryEngine
from src.rag.retrieval import (
    BM25Retriever,
    BaseRetriever,
    CrossEncoderReranker,
    HybridRetriever,
    PassThroughReranker,
    RankFusionService,
    RetrievalTelemetry,
)


def chunk(
    content: str,
    score: float,
    index: int,
    filename: str = "policy.md",
    document_hash: str = "hash",
) -> RetrievedChunk:
    return RetrievedChunk(
        content=content,
        similarity_score=score,
        source_filename=filename,
        source_document_hash=document_hash,
        chunk_index=index,
        metadata={"chunk_id": f"{document_hash}:{index}"},
    )


class StaticRetriever(BaseRetriever):
    def __init__(self, chunks: List[RetrievedChunk]) -> None:
        self.chunks = chunks

    def retrieve(self, query: RAGQuery) -> List[RetrievedChunk]:
        return self.chunks[: query.top_k]


class ScoreReranker(PassThroughReranker):
    @property
    def name(self) -> str:
        return "score_reranker"

    def rerank(self, query: RAGQuery, chunks: List[RetrievedChunk], top_k: int) -> List[RetrievedChunk]:
        return sorted(chunks, key=lambda item: item.metadata.get("rerank_score", 0), reverse=True)[:top_k]


def test_bm25_retrieval_returns_keyword_matches():
    retriever = BM25Retriever(
        [
            chunk("prior authorization required for infusion", 0.1, 0),
            chunk("diabetes medication refill workflow", 0.1, 1),
        ]
    )

    results = retriever.retrieve(RAGQuery(query_text="prior authorization", top_k=5))

    assert len(results) == 1
    assert "prior authorization" in results[0].content
    assert results[0].metadata["retrieval_strategy"] == "bm25"


def test_bm25_no_overlap_returns_empty_list():
    retriever = BM25Retriever([chunk("clinical policy", 0.1, 0)])

    results = retriever.retrieve(RAGQuery(query_text="unrelated phrase", top_k=5))

    assert results == []


def test_rank_fusion_correctness_and_duplicate_merge():
    duplicate_dense = chunk("same evidence dense", 0.9, 0)
    duplicate_sparse = chunk("same evidence sparse", 0.7, 0)
    dense_only = chunk("dense only", 0.8, 1)
    sparse_only = chunk("sparse only", 0.6, 2)
    fusion = RankFusionService(rrf_k=10)

    results = fusion.reciprocal_rank_fusion(
        ranked_lists=[[duplicate_dense, dense_only], [duplicate_sparse, sparse_only]],
        top_k=10,
    )

    ids = [item.metadata["chunk_id"] for item in results]
    assert ids.count("hash:0") == 1
    assert ids[0] == "hash:0"
    assert results[0].metadata["rrf_score"] > results[1].metadata["rrf_score"]


def test_rank_fusion_deterministic_tie_breaking():
    a = chunk("alpha", 0.5, 2, document_hash="b")
    b = chunk("beta", 0.5, 1, document_hash="a")
    fusion = RankFusionService(rrf_k=60)

    first = fusion.reciprocal_rank_fusion([[a], [b]], top_k=2)
    second = fusion.reciprocal_rank_fusion([[a], [b]], top_k=2)

    assert [item.metadata["chunk_id"] for item in first] == ["a:1", "b:2"]
    assert [item.metadata["chunk_id"] for item in first] == [
        item.metadata["chunk_id"] for item in second
    ]


def test_hybrid_retrieval_dense_only_path():
    dense = [chunk("semantic match", 0.9, 0)]
    hybrid = HybridRetriever(
        vector_retriever=StaticRetriever(dense),
        bm25_retriever=BM25Retriever([]),
        rank_fusion_service=RankFusionService(rrf_k=10),
        reranker=PassThroughReranker(),
        hybrid_top_k=5,
        rerank_top_k=5,
    )

    results = hybrid.retrieve(RAGQuery(query_text="anything", top_k=5))

    assert len(results) == 1
    assert results[0].content == "semantic match"
    assert hybrid.last_telemetry.retrieved_candidate_count == 1


def test_hybrid_retrieval_sparse_only_path():
    sparse = BM25Retriever([chunk("prior auth sparse hit", 0.1, 0)])
    hybrid = HybridRetriever(
        vector_retriever=StaticRetriever([]),
        bm25_retriever=sparse,
        rank_fusion_service=RankFusionService(rrf_k=10),
        reranker=PassThroughReranker(),
        hybrid_top_k=5,
        rerank_top_k=5,
    )

    results = hybrid.retrieve(RAGQuery(query_text="prior auth", top_k=5))

    assert len(results) == 1
    assert "sparse hit" in results[0].content


def test_hybrid_retrieval_no_overlap_returns_empty_list():
    hybrid = HybridRetriever(
        vector_retriever=StaticRetriever([]),
        bm25_retriever=BM25Retriever([chunk("clinical policy", 0.1, 0)]),
        rank_fusion_service=RankFusionService(rrf_k=10),
        reranker=PassThroughReranker(),
        hybrid_top_k=5,
        rerank_top_k=5,
    )

    results = hybrid.retrieve(RAGQuery(query_text="unrelated", top_k=5))

    assert results == []


def test_reranker_sorting_with_injected_model():
    class FakeModel:
        def predict(self, pairs):
            return [0.1, 0.9]

    reranker = CrossEncoderReranker(model=FakeModel())
    chunks = [chunk("low", 0.5, 0), chunk("high", 0.5, 1)]

    results = reranker.rerank(RAGQuery(query_text="question"), chunks, top_k=2)

    assert results[0].content == "high"
    assert results[0].metadata["reranker"] == "cross_encoder"


def test_reranker_fallback_preserves_order_for_failures():
    class BrokenModel:
        def predict(self, pairs):
            raise RuntimeError("model unavailable")

    reranker = CrossEncoderReranker(model=BrokenModel())
    chunks = [chunk("first", 0.5, 0), chunk("second", 0.5, 1)]

    results = reranker.rerank(RAGQuery(query_text="question"), chunks, top_k=2)

    assert [item.content for item in results] == ["first", "second"]


def test_retrieval_telemetry_model():
    telemetry = RetrievalTelemetry(
        vector_retrieval_time_ms=1.0,
        bm25_retrieval_time_ms=2.0,
        fusion_time_ms=3.0,
        reranking_time_ms=4.0,
        retrieved_candidate_count=5,
        reranked_candidate_count=2,
        reranker_name="test",
    )

    assert telemetry.retrieved_candidate_count == 5
    assert telemetry.reranker_name == "test"


def test_retrieval_configuration_loading():
    settings = get_settings()

    assert settings.RRF_K >= 1
    assert settings.HYBRID_TOP_K >= 1
    assert settings.RERANK_TOP_K >= 1


def test_query_engine_accepts_base_retriever_integration():
    retriever = StaticRetriever([chunk("prior authorization is required", 0.9, 0)])
    engine = QueryEngine(
        retriever=retriever,
        llm_provider=MockLLMProvider(fixed_response="Prior authorization is required [1]."),
        embedding_provider_name="fake",
    )

    response = engine.execute(RAGQuery(query_text="Is prior authorization required?"))

    assert isinstance(engine.retriever, BaseRetriever)
    assert response.answer == "Prior authorization is required [1]."
    assert response.citations == ["[1] [policy.md | chunk 0]"]
