"""KPI metrics display helpers for the EAKAP Enterprise Console.

Wraps Streamlit's native ``st.metric`` in convenience helpers that enforce
consistent sizing and layout across all console tabs.
"""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def render_kpi_row(metrics: Dict[str, Any]) -> None:
    """Render a single row of KPI metric tiles.

    Args:
        metrics: Ordered mapping of ``label → value``. Up to 6 items display
                 cleanly; beyond that Streamlit wraps automatically.

    Example::

        render_kpi_row({"Queries": 42, "Avg Latency": "320 ms", "PII": 0})
    """
    if not metrics:
        return
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics.items()):
        with col:
            st.metric(label=label, value=str(value))


def render_latency_metrics(
    retrieval_ms: float,
    generation_ms: float,
    total_ms: float,
) -> None:
    """Render a three-column RAG pipeline latency breakdown.

    Args:
        retrieval_ms:  Chunk retrieval time in milliseconds.
        generation_ms: LLM generation time in milliseconds.
        total_ms:      End-to-end pipeline time in milliseconds.
    """
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="⏱ Retrieval", value=f"{retrieval_ms:.0f} ms")
    with col2:
        st.metric(label="🤖 Generation", value=f"{generation_ms:.0f} ms")
    with col3:
        st.metric(label="🔁 Total", value=f"{total_ms:.0f} ms")


def render_analytics_latency(
    sql_gen_ms: float,
    sql_exec_ms: float,
    total_ms: float,
) -> None:
    """Render a three-column Conversational BI latency breakdown.

    Args:
        sql_gen_ms:  SQL generation time in milliseconds.
        sql_exec_ms: SQL execution time in milliseconds.
        total_ms:    End-to-end pipeline time in milliseconds.
    """
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="🔧 SQL Gen", value=f"{sql_gen_ms:.0f} ms")
    with col2:
        st.metric(label="⚡ Execution", value=f"{sql_exec_ms:.0f} ms")
    with col3:
        st.metric(label="🔁 Total", value=f"{total_ms:.0f} ms")
