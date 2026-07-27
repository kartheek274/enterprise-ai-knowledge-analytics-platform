"""Conversational BI tab renderer — EAKAP Enterprise Console.

Presents a natural-language analytics interface backed by
``ConversationalBIEngine``. The engine handles schema inspection, SQL
generation, validation, execution, and summary generation. This module
only handles display.
"""

from __future__ import annotations

import logging

import streamlit as st

from src.analytics.models import SQLQueryRequest
from src.analytics.pipeline import ConversationalBIEngine
from src.app.ui.components.badges import render_sql_validation_badge
from src.app.ui.components.charts import auto_chart
from src.app.ui.components.metrics import render_analytics_latency
from src.app.ui.state import UIStateManager

logger = logging.getLogger("eakap.app.ui.bi_tab")


def render_bi_tab(
    state: UIStateManager,
    bi_engine: ConversationalBIEngine,
) -> None:
    """Render the 📊 Conversational BI interface.

    Args:
        state:     Shared UI state manager.
        bi_engine: Pre-built ``ConversationalBIEngine`` (injected by
                   ``main_app.py`` via ``@st.cache_resource``).
    """
    import pandas as pd

    st.markdown("#### Natural Language Analytics")
    st.caption(
        "Ask business questions in plain English. The platform generates and "
        "validates SQL, executes it safely against the data warehouse, and "
        "provides a business-friendly summary."
    )

    # ---- Question input ------------------------------------------------
    question = st.text_area(
        "Your business question",
        placeholder=(
            "e.g. Show total claim amounts by state for approved claims…"
        ),
        key="bi_question_input",
        height=80,
        label_visibility="collapsed",
    )

    run_clicked = st.button(
        "▶ Run Analysis",
        key="bi_run_btn",
        type="primary",
        use_container_width=False,
    )

    if not run_clicked:
        return

    if not question.strip():
        st.warning("Please enter a question before running the analysis.")
        return

    with st.spinner("Generating SQL and running analysis…"):
        try:
            request = SQLQueryRequest(question=question.strip())
            response = bi_engine.execute(request)

            # ---- Section 1: Generated SQL ------------------------------
            st.markdown("---")
            st.markdown("**🔧 Generated SQL**")
            render_sql_validation_badge(is_valid=True)
            st.code(response.generated_sql, language="sql")

            # ---- Section 2: Results DataFrame --------------------------
            st.markdown("**📋 Query Results**")
            result = response.execution_result

            if result.rows:
                df = pd.DataFrame(result.rows, columns=result.columns)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(
                    f"{result.row_count} row(s) returned "
                    f"in {result.execution_time_ms:.0f} ms"
                )

                # ---- Section 3: Auto Chart --------------------------
                auto_chart(result.rows, result.columns)
            else:
                st.info("The query returned no rows.")

            # ---- Section 4: Business Explanation ----------------------
            st.markdown("**💡 Business Insight**")
            st.info(response.summary)

            # ---- Section 5: Performance --------------------------------
            with st.expander("⏱️ Performance", expanded=False):
                render_analytics_latency(
                    sql_gen_ms=response.telemetry.sql_generation_ms,
                    sql_exec_ms=response.telemetry.sql_execution_ms,
                    total_ms=response.telemetry.total_execution_ms,
                )

            # ---- Persist to telemetry log ------------------------------
            state.append_telemetry(
                {
                    "source": "bi",
                    "question": question.strip(),
                    "sql": response.generated_sql,
                    "row_count": result.row_count,
                    "sql_gen_ms": response.telemetry.sql_generation_ms,
                    "sql_exec_ms": response.telemetry.sql_execution_ms,
                    "total_ms": response.telemetry.total_execution_ms,
                    "status": response.telemetry.status,
                    "model": response.telemetry.model_name,
                }
            )

        except Exception as exc:
            st.error(f"⚠️ Analysis failed: {exc}")
            logger.error("BI query execution failed: %s", exc, exc_info=True)
