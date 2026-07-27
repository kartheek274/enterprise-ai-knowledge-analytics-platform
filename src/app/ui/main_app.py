"""EAKAP Enterprise Console — Streamlit Entrypoint.

Step 10: Streamlit UI Implementation.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys

# Ensure project root directory is in sys.path when running via `streamlit run`
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from src.analytics.pipeline.bi_engine import ConversationalBIEngine
from src.app.health_service import HealthService
from src.app.ui.components.bi_tab import render_bi_tab
from src.app.ui.components.governance_tab import render_governance_tab
from src.app.ui.components.rag_tab import render_rag_tab
from src.app.ui.components.sidebar import render_sidebar
from src.app.ui.state import UIStateManager
from src.governance.service import GovernanceService
from src.rag.pipeline.query_engine import QueryEngine

logger = logging.getLogger("eakap.app.ui.main_app")

# Page Configuration
st.set_page_config(
    page_title="EAKAP Enterprise Console",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Cache version token — increment this string whenever backend code changes
# to force Streamlit to invalidate its @st.cache_resource objects.
# This guarantees the running app always uses the latest service instances.
# ---------------------------------------------------------------------------
_CACHE_VERSION = "v20260727-1"


@st.cache_resource
def get_query_engine(_version: str = _CACHE_VERSION) -> QueryEngine:
    """Initialize and cache the QueryEngine singleton for RAG pipeline."""
    import logging as _log
    _log.getLogger("eakap.app.ui.main_app").info(
        "Initializing QueryEngine (cache_version=%s)", _version
    )
    return QueryEngine()


@st.cache_resource
def get_bi_engine(_version: str = _CACHE_VERSION) -> ConversationalBIEngine:
    """Initialize and cache the ConversationalBIEngine singleton."""
    import logging as _log
    _log.getLogger("eakap.app.ui.main_app").info(
        "Initializing ConversationalBIEngine (cache_version=%s)", _version
    )
    engine = ConversationalBIEngine()
    _log.getLogger("eakap.app.ui.main_app").info(
        "ConversationalBIEngine ready | llm_provider=%s | sql_generator_llm=%s",
        engine.llm_provider.__class__.__name__,
        engine.sql_generator.llm_provider.__class__.__name__,
    )
    return engine


@st.cache_resource
def get_governance_service(_version: str = _CACHE_VERSION) -> GovernanceService:
    """Initialize and cache the GovernanceService singleton."""
    return GovernanceService()


@st.cache_resource
def get_health_service(_version: str = _CACHE_VERSION) -> HealthService:
    """Initialize and cache the HealthService singleton."""
    return HealthService()


def main() -> None:
    """Main application loop for Streamlit UI."""
    state = UIStateManager()
    state.initialize()

    # Load core services
    query_engine = get_query_engine()
    bi_engine = get_bi_engine()
    governance_service = get_governance_service()
    health_service = get_health_service()

    # Render Sidebar
    render_sidebar(state=state, health_service=health_service)

    # Main Header
    st.title("🏢 Enterprise AI Knowledge & Analytics Platform")
    st.caption("Unified Enterprise RAG, Conversational BI, and AI Governance Console")
    st.divider()

    # Enterprise Tabs
    tab_rag, tab_bi, tab_gov = st.tabs(
        [
            "🧠 Knowledge Assistant",
            "📊 Conversational BI",
            "🛡 Governance & Observability",
        ]
    )

    with tab_rag:
        render_rag_tab(state=state, query_engine=query_engine)

    with tab_bi:
        render_bi_tab(state=state, bi_engine=bi_engine)

    with tab_gov:
        render_governance_tab(state=state, governance_service=governance_service)


if __name__ == "__main__":
    main()
