"""Rank fusion algorithms for hybrid retrieval."""

from typing import Dict, Iterable, List, Tuple

from src.common.config.settings import get_settings
from src.rag.models.retrieved_chunk import RetrievedChunk


class RankFusionService:
    """Merge ranked retrieval result lists using Reciprocal Rank Fusion."""

    def __init__(self, rrf_k: int | None = None) -> None:
        self.rrf_k = rrf_k or get_settings().RRF_K

    def reciprocal_rank_fusion(
        self,
        ranked_lists: Iterable[List[RetrievedChunk]],
        top_k: int,
    ) -> List[RetrievedChunk]:
        """Fuse result lists deterministically by RRF score."""
        fused_scores: Dict[str, float] = {}
        best_chunks: Dict[str, RetrievedChunk] = {}

        for ranked_list in ranked_lists:
            for rank, chunk in enumerate(ranked_list, start=1):
                chunk_id = self._chunk_id(chunk)
                fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + 1.0 / (self.rrf_k + rank)
                current = best_chunks.get(chunk_id)
                if current is None or chunk.similarity_score > current.similarity_score:
                    best_chunks[chunk_id] = chunk

        ordered: List[Tuple[str, float, RetrievedChunk]] = [
            (chunk_id, score, best_chunks[chunk_id])
            for chunk_id, score in fused_scores.items()
        ]
        ordered.sort(
            key=lambda item: (
                -item[1],
                -item[2].similarity_score,
                self._stable_key(item[2]),
            )
        )

        if not ordered:
            return []

        max_score = ordered[0][1] or 1.0
        results: List[RetrievedChunk] = []
        for _, fused_score, chunk in ordered[:top_k]:
            results.append(
                chunk.model_copy(
                    update={
                        "similarity_score": min(1.0, fused_score / max_score),
                        "metadata": {
                            **chunk.metadata,
                            "rrf_score": fused_score,
                            "retrieval_strategy": "hybrid",
                        },
                    }
                )
            )
        return results

    @staticmethod
    def _chunk_id(chunk: RetrievedChunk) -> str:
        if chunk.metadata.get("chunk_id"):
            return str(chunk.metadata["chunk_id"])
        if chunk.source_document_hash:
            return f"{chunk.source_document_hash}:{chunk.chunk_index}"
        return f"{chunk.source_filename}:{chunk.chunk_index}:{chunk.content[:64]}"

    @staticmethod
    def _stable_key(chunk: RetrievedChunk) -> str:
        return RankFusionService._chunk_id(chunk)
