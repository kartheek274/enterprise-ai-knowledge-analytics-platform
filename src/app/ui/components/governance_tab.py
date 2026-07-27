"""Governance & Observability tab renderer — EAKAP Enterprise Console.

Aggregates session telemetry, governance metrics, configuration settings,
and guardrail registry into a single audit-friendly dashboard view.
"""

from __future__ import annotations

import logging
from typing import Optional

import streamlit as st

from src.app.ui.components.cards import render_section_card
from src.app.ui.components.tables import render_dict_table, render_telemetry_table
from src.app.ui.state import UIStateManager
from src.common.config.settings import get_settings
from src.governance.service import GovernanceService

logger = logging.getLogger("eakap.app.ui.governance_tab")

# Keys that must be redacted in the configuration display
_REDACT_KEYS = ["SECRET_KEY", "DATABASE_URL"]


def render_governance_tab(
    state: UIStateManager,
    governance_service: Optional[GovernanceService] = None,
) -> None:
    """Render the 🛡 Governance & Observability tab.

    Args:
        state:              Shared UI state manager.
        governance_service: Optional pre-built ``GovernanceService`` instance.
                            Constructed lazily if not supplied.
    """
    st.markdown("#### Governance Dashboard & Observability")
    st.caption(
        "Real-time telemetry, PII detection counts, prompt injection monitoring, "
        "guardrail configuration, and application settings."
    )

    logs = state.get_telemetry_logs()

    # ---- 1. Session Telemetry Summary ----------------------------------
    render_section_card("Session Telemetry Summary", "📊")
    rag_logs = [l for l in logs if l.get("source") == "rag"]
    bi_logs = [l for l in logs if l.get("source") == "bi"]
    pii_count = sum(int(l.get("pii_count", 0)) for l in rag_logs)
    injection_count = sum(
        int(l.get("injection_attempts", 0)) for l in rag_logs
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🧠 RAG Queries", len(rag_logs))
    with col2:
        st.metric("📊 BI Queries", len(bi_logs))
    with col3:
        st.metric("🛡️ PII Detections", pii_count)
    with col4:
        st.metric("⚠️ Injection Attempts", injection_count)

    # ---- 2. Telemetry Log Table ----------------------------------------
    st.divider()
    render_section_card("Telemetry Log", "📋")
    render_telemetry_table(logs)

    # ---- 3. Governance Configuration -----------------------------------
    st.divider()
    render_section_card("Governance Configuration", "🛡️")

    try:
        settings = get_settings()

        col_a, col_b = st.columns([1, 1])

        with col_a:
            st.markdown("**Active Guardrail Settings**")
            governance_flags = {
                "GUARDRAIL_STRICT_MODE": settings.GUARDRAIL_STRICT_MODE,
                "ENABLE_INPUT_GUARDRAILS": settings.ENABLE_INPUT_GUARDRAILS,
                "ENABLE_OUTPUT_GUARDRAILS": settings.ENABLE_OUTPUT_GUARDRAILS,
                "ENABLE_PII_REDACTION": settings.ENABLE_PII_REDACTION,
            }
            for key, val in governance_flags.items():
                tick = "✅" if val else "❌"
                label = key.replace("_", " ").title()
                st.markdown(f"{tick} **{label}**: `{val}`")

        with col_b:
            st.markdown("**Guardrail Registry**")
            try:
                _gov = governance_service or GovernanceService()
                registry = _gov.guardrail_registry()
                st.json(registry)
            except Exception as exc:
                st.warning(f"Registry unavailable: {exc}")
                logger.warning("Guardrail registry load failed: %s", exc)

    except Exception as exc:
        st.error(f"Could not load governance configuration: {exc}")
        logger.error("Governance config load failed: %s", exc)

    # ---- 4. Full Application Configuration ----------------------------
    st.divider()
    with st.expander("⚙️ Full Application Configuration", expanded=False):
        try:
            settings = get_settings()
            config_dict = settings.model_dump()
            render_dict_table(
                data=config_dict,
                title="All Settings (sensitive keys redacted)",
                redact_keys=_REDACT_KEYS,
            )
        except Exception as exc:
            st.error(f"Could not load settings: {exc}")
            logger.error("Settings model_dump failed: %s", exc)
