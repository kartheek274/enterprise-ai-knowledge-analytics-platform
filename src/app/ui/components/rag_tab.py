"""Knowledge Assistant (RAG) tab renderer — EAKAP Enterprise Console.

Presents a chat interface backed by ``QueryEngine``. All conversation state
is persisted through ``UIStateManager``. Business logic stays in the engine;
this module is intentionally thin.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import streamlit as st

from src.app.ui.components.badges import render_pii_badge
from src.app.ui.components.metrics import render_latency_metrics
from src.app.ui.components.tables import render_citations_table
from src.app.ui.state import UIStateManager
from src.rag.models.query import RAGQuery
from src.rag.pipeline.query_engine import QueryEngine

logger = logging.getLogger("eakap.app.ui.rag_tab")


def render_rag_tab(state: UIStateManager, query_engine: QueryEngine) -> None:
    """Render the 🧠 Knowledge Assistant chat interface.

    Args:
        state:        Shared UI state manager.
        query_engine: Pre-built ``QueryEngine`` instance (injected by
                      ``main_app.py`` via ``@st.cache_resource``).
    """
    st.markdown("#### Ask the Enterprise Knowledge Base")
    st.caption(
        "Queries are grounded in indexed documents via Hybrid RAG "
        "(vector + BM25 + reranking). PII is automatically redacted from responses."
    )

    # ---- Replay existing conversation history --------------------------
    for turn in state.get_chat_history():
        role = turn.get("role", "user")
        content = turn.get("content", "")
        metadata = turn.get("metadata", {})

        with st.chat_message(role):
            st.markdown(content)
            if role == "assistant" and metadata:
                _render_assistant_extras(metadata)

    # ---- Chat input ----------------------------------------------------
    user_input: str | None = st.chat_input(
        "Ask the knowledge base…", key="rag_chat_input"
    )

    if not user_input:
        return

    # Display user turn immediately
    with st.chat_message("user"):
        st.markdown(user_input)
    state.add_chat_turn("user", user_input)

    # Execute RAG pipeline
    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base…"):
            query = RAGQuery(
                query_text=user_input,
                session_id=state.get_session_id(),
            )
            try:
                response = query_engine.execute_with_error_response(query)

                st.markdown(response.answer)

                # ---- Governance metadata --------------------------------
                governance: Dict[str, Any] = response.execution_metadata.get(
                    "governance", {}
                )
                pii_redacted = governance.get("redaction_count", 0) > 0

                # ---- Serialise chunks for state persistence -------------
                serialised_chunks: List[Dict[str, Any]] = [
                    {
                        "source_filename": c.source_filename,
                        "chunk_index": c.chunk_index,
                        "similarity_score": c.similarity_score,
                        "content": c.content,
                    }
                    for c in response.retrieved_chunks
                ]

                meta: Dict[str, Any] = {
                    "telemetry": {
                        "retrieval_time_ms": response.telemetry.retrieval_time_ms,
                        "generation_time_ms": response.telemetry.generation_time_ms,
                        "total_time_ms": response.telemetry.total_time_ms,
                        "status": response.telemetry.status,
                    },
                    "chunks": serialised_chunks,
                    "citations": response.citations,
                    "pii_redacted": pii_redacted,
                    "governance": governance,
                }

                _render_assistant_extras(meta)

                state.add_chat_turn("assistant", response.answer, meta)

                # Accumulate telemetry for governance tab
                state.append_telemetry(
                    {
                        "source": "rag",
                        "query": user_input,
                        "status": response.telemetry.status,
                        "retrieval_ms": response.telemetry.retrieval_time_ms,
                        "generation_ms": response.telemetry.generation_time_ms,
                        "total_ms": response.telemetry.total_time_ms,
                        "chunks": len(serialised_chunks),
                        "pii_redacted": pii_redacted,
                        "pii_count": governance.get("redaction_count", 0),
                        "injection_attempts": governance.get(
                            "input_violation_count", 0
                        ),
                    }
                )

            except Exception as exc:
                error_msg = f"⚠️ Query failed: {exc}"
                st.error(error_msg)
                state.add_chat_turn("assistant", error_msg)
                logger.error("RAG query execution failed: %s", exc, exc_info=True)


# --------------------------------------------------------------------------- #
# Internal helpers                                                              #
# --------------------------------------------------------------------------- #

def _render_assistant_extras(metadata: Dict[str, Any]) -> None:
    """Render PII badge, latency panel, and citation table below an answer."""
    if metadata.get("pii_redacted"):
        render_pii_badge()

    telemetry = metadata.get("telemetry", {})
    chunks = metadata.get("chunks", [])

    if telemetry:
        with st.expander("⏱️ Performance", expanded=False):
            render_latency_metrics(
                retrieval_ms=float(telemetry.get("retrieval_time_ms", 0.0)),
                generation_ms=float(telemetry.get("generation_time_ms", 0.0)),
                total_ms=float(telemetry.get("total_time_ms", 0.0)),
            )

    if chunks:
        with st.expander(f"📎 Citations ({len(chunks)})", expanded=False):
            render_citations_table(_ChunkProxy(c) for c in chunks)


class _ChunkProxy:
    """Lightweight proxy exposing dict-stored chunk data as attributes.

    Allows ``render_citations_table`` to work with both real
    ``RetrievedChunk`` objects and the serialised dicts stored in session state.
    """

    __slots__ = (
        "source_filename",
        "chunk_index",
        "similarity_score",
        "content",
    )

    def __init__(self, data: Dict[str, Any]) -> None:
        self.source_filename: str = str(data.get("source_filename", "unknown"))
        self.chunk_index: int = int(data.get("chunk_index", 0))
        self.similarity_score: float = float(data.get("similarity_score", 0.0))
        self.content: str = str(data.get("content", ""))
