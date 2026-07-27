"""Hybrid retriever coordinating dense, sparse, fusion, and reranking services."""

import logging
import time
from typing import List, Optional

from src.common.config.settings import get_settings
from src.common.errors.exceptions import RetrievalError
from src.rag.models.query import RAGQuery
from src.rag.models.retrieved_chunk import RetrievedChunk
from src.rag.retrieval.base import BaseRetriever
from src.rag.retrieval.bm25_retriever import BM25Retriever
from src.rag.retrieval.rank_fusion import RankFusionService
from src.rag.retrieval.reranker import BaseReranker, PassThroughReranker
from src.rag.retrieval.telemetry import RetrievalTelemetry

logger = logging.getLogger("eakap.rag.hybrid_retriever")


class HybridRetriever(BaseRetriever):
    """Retrieve candidates from dense and sparse retrievers, then fuse and rerank."""

    def __init__(
        self,
        vector_retriever: BaseRetriever,
        bm25_retriever: BM25Retriever,
        rank_fusion_service: Optional[RankFusionService] = None,
        reranker: Optional[BaseReranker] = None,
        hybrid_top_k: Optional[int] = None,
        rerank_top_k: Optional[int] = None,
    ) -> None:
        settings = get_settings()
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever
        self.rank_fusion_service = rank_fusion_service or RankFusionService()
        self.reranker = reranker or PassThroughReranker()
        self.hybrid_top_k = hybrid_top_k or settings.HYBRID_TOP_K
        self.rerank_top_k = rerank_top_k or settings.RERANK_TOP_K
        self.last_telemetry = RetrievalTelemetry(reranker_name=self.reranker.name)

    def retrieve(self, query: RAGQuery) -> List[RetrievedChunk]:
        """Return fused and reranked retrieval candidates."""
        telemetry = RetrievalTelemetry(reranker_name=self.reranker.name)
        try:
            dense_query = query.model_copy(update={"top_k": self.hybrid_top_k})
            start = time.perf_counter()
            dense_results = self.vector_retriever.retrieve(dense_query)
            telemetry.vector_retrieval_time_ms = (time.perf_counter() - start) * 1_000

            sparse_query = query.model_copy(update={"top_k": self.hybrid_top_k})
            start = time.perf_counter()
            sparse_results = self.bm25_retriever.retrieve(sparse_query)
            telemetry.bm25_retrieval_time_ms = (time.perf_counter() - start) * 1_000

            start = time.perf_counter()
            fused = self.rank_fusion_service.reciprocal_rank_fusion(
                ranked_lists=[dense_results, sparse_results],
                top_k=self.hybrid_top_k,
            )
            telemetry.fusion_time_ms = (time.perf_counter() - start) * 1_000
            telemetry.retrieved_candidate_count = len(fused)

            start = time.perf_counter()
            reranked = self.reranker.rerank(
                query=query,
                chunks=fused,
                top_k=min(query.top_k, self.rerank_top_k),
            )
            telemetry.reranking_time_ms = (time.perf_counter() - start) * 1_000
            telemetry.reranked_candidate_count = len(reranked)
            telemetry.reranker_name = self.reranker.name
            self.last_telemetry = telemetry
            logger.info(
                "Hybrid retrieval completed | dense=%s | sparse=%s | fused=%s | final=%s",
                len(dense_results),
                len(sparse_results),
                len(fused),
                len(reranked),
            )
            return reranked
        except RetrievalError:
            raise
        except Exception as exc:
            raise RetrievalError(
                message="Hybrid retrieval failed.",
                original_exception=exc,
            )
