"""Sidebar renderer for the EAKAP Enterprise Console.

Renders application health indicators, session management controls, and
platform metadata. All health data is sourced through ``HealthService``
to remain decoupled from the CLI entrypoint.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import streamlit as st

from src.app.health_service import HealthService
from src.app.ui.components.badges import render_status_badge
from src.app.ui.components.cards import render_section_card
from src.app.ui.state import UIStateManager

logger = logging.getLogger("eakap.app.ui.sidebar")

# --------------------------------------------------------------------------- #
# Component registry — ordered list of (health_key, display_label)             #
# --------------------------------------------------------------------------- #
_HEALTH_COMPONENTS = [
    ("configuration", "Configuration", "⚙️"),
    ("llm_provider", "LLM Provider", "🤖"),
    ("vector_store", "Vector DB", "🗂️"),
    ("database", "Database", "🗄️"),
    ("memory", "Memory Store", "🧠"),
    ("embeddings", "Embeddings", "🔢"),
    ("advanced_retrieval", "Retrieval Engine", "🔍"),
    ("governance", "Governance", "🛡️"),
    ("prompt_manager", "Prompt Manager", "📝"),
    ("analytics", "Analytics Engine", "📊"),
]


@st.cache_data(ttl=60)
def _get_cached_health_status(_health_service: HealthService) -> Tuple[bool, Dict[str, Any]]:
    """Cached wrapper around HealthService.run with 60s TTL to prevent expensive reruns."""
    return _health_service.run()


def render_sidebar(
    state: UIStateManager,
    health_service: Optional[HealthService] = None,
) -> None:
    """Render the full application sidebar.

    Args:
        state:          Shared UI state manager.
        health_service: Optional pre-built ``HealthService`` (useful for
                        testing or when the caller owns service lifecycle).
    """
    _hs = health_service or HealthService()

    with st.sidebar:
        # ---- Header --------------------------------------------------------
        st.markdown(
            """
            <div style="text-align:center;padding:12px 0 4px 0;">
                <div style="font-size:1.6rem;">🏢</div>
                <div style="font-weight:700;font-size:1.1rem;color:#fafafa;">
                    EAKAP Console
                </div>
                <div style="font-size:0.75rem;color:#a0a0b0;">
                    Enterprise AI Platform
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        # ---- Platform Health ------------------------------------------------
        render_section_card("Platform Health", "🔍")

        if st.button("🔄 Refresh Status", key="sidebar_refresh_health", use_container_width=True):
            _get_cached_health_status.clear()
            st.rerun()

        try:
            is_healthy, details = _get_cached_health_status(_hs)

            # Overall status pill
            if is_healthy:
                st.success("🟢 All Systems Operational", icon=None)
            else:
                st.error("🔴 Platform Degraded", icon=None)

            # Individual component health indicators
            with st.expander(
                "Component Status", expanded=not is_healthy
            ):
                for key, label, icon in _HEALTH_COMPONENTS:
                    component = details.get(key, {})
                    status = HealthService.extract_status(component)

                    status_icon = (
                        "✅" if status == "healthy"
                        else "❌" if status == "unhealthy"
                        else "⚠️"
                    )
                    st.markdown(
                        f"{status_icon}&nbsp;**{icon} {label}**&nbsp;`{status}`"
                    )

                    # Contextual sub-details for key components
                    if isinstance(component, dict) and status == "healthy":
                        _render_component_detail(key, component)

        except Exception as exc:
            st.warning(f"Health check unavailable: {exc}")
            logger.warning("Health check failed in sidebar: %s", exc)

        st.divider()

        # ---- Session Management --------------------------------------------
        render_section_card("Session", "🗂️")

        current_id = state.get_session_id()
        st.code(current_id[:8] + "…", language=None)
        st.caption("Current session ID (first 8 chars)")

        custom_id = st.text_input(
            "Custom Session ID",
            value="",
            placeholder="Enter or paste a session ID…",
            key="sidebar_session_input",
            label_visibility="collapsed",
        )

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button(
                "🔄 Set",
                use_container_width=True,
                key="sidebar_set_session",
                help="Switch to the typed session ID",
            ):
                if custom_id.strip():
                    state.set_session_id(custom_id.strip())
                    st.rerun()
        with btn_col2:
            if st.button(
                "🗑️ Clear",
                use_container_width=True,
                key="sidebar_clear_session",
                type="secondary",
                help="Reset conversation and generate a new session",
            ):
                state.clear_session()
                st.rerun()

        st.divider()

        # ---- Footer --------------------------------------------------------
        st.caption("EAKAP v1.1 · Step 10 · Streamlit Console")


# --------------------------------------------------------------------------- #
# Internal helpers                                                              #
# --------------------------------------------------------------------------- #

def _render_component_detail(key: str, component: dict) -> None:
    """Render concise sub-details for a healthy component."""
    if key == "llm_provider":
        provider = component.get("provider", "")
        model = component.get("model", "")
        if provider:
            st.caption(f"  └ {provider} / {model}")
    elif key == "vector_store":
        count = component.get("collections_count", 0)
        directory = component.get("directory", "")
        st.caption(f"  └ {count} collections · {directory}")
    elif key == "database":
        tables = component.get("tables_present", [])
        st.caption(f"  └ {len(tables)} tables: {', '.join(tables[:3])}")
    elif key == "memory":
        sessions = component.get("components", {}).get("sessions", 0)
        strategy = component.get("configuration", {}).get(
            "compression_strategy", ""
        )
        st.caption(f"  └ {sessions} sessions · {strategy}")
    elif key == "embeddings":
        provider = component.get("provider", "")
        dim = component.get("dimension", 0)
        st.caption(f"  └ {provider} ({dim}d)")
    elif key == "configuration":
        env = component.get("environment", "")
        st.caption(f"  └ environment: {env}")
    elif key == "analytics":
        tables = component.get("business_tables", [])
        st.caption(f"  └ {len(tables)} business tables")
    elif key == "advanced_retrieval":
        cfg = component.get("configuration", {})
        rrf = cfg.get("rrf_k", "")
        topk = cfg.get("hybrid_top_k", "")
        st.caption(f"  └ RRF k={rrf} · top_k={topk}")
