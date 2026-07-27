"""Status and annotation badge helpers for the EAKAP Enterprise Console.

Badges are rendered as inline HTML spans using ``st.markdown`` with
``unsafe_allow_html=True``. All colours are drawn from the enterprise
dark theme palette.
"""

from __future__ import annotations

import streamlit as st

# ---------- colour constants ----------
_GREEN = "#00C851"
_RED = "#FF4B4B"
_AMBER = "#FFB300"
_PURPLE = "#6C63FF"
_GREY = "#9E9E9E"
_BLUE = "#2196F3"

_BADGE_STYLE = (
    "display:inline-block;"
    "padding:2px 10px;"
    "border-radius:4px;"
    "font-size:0.78rem;"
    "font-weight:600;"
    "color:white;"
    "margin:2px 0;"
)


def _badge(text: str, colour: str) -> str:
    """Build an inline-styled HTML badge span."""
    return (
        f'<span style="{_BADGE_STYLE}background:{colour};">'
        f"{text}</span>"
    )


def render_pii_badge() -> None:
    """Render a prominent PII-screened badge below an assistant response.

    Shown whenever ``GovernanceTelemetry.redaction_count > 0``.
    """
    st.markdown(_badge("🛡️ PII Screened", _RED), unsafe_allow_html=True)


def render_status_badge(status: str) -> None:
    """Render a component health status badge.

    Args:
        status: One of ``"healthy"``, ``"unhealthy"``, or ``"unknown"``.
    """
    status_lower = status.lower()
    if status_lower == "healthy":
        colour, icon = _GREEN, "✅"
    elif status_lower == "unhealthy":
        colour, icon = _RED, "❌"
    else:
        colour, icon = _AMBER, "⚠️"

    st.markdown(
        _badge(f"{icon} {status.upper()}", colour),
        unsafe_allow_html=True,
    )


def render_sql_validation_badge(is_valid: bool) -> None:
    """Render an SQL validation result badge.

    Args:
        is_valid: ``True`` when the SQL passed enterprise validation.
    """
    if is_valid:
        st.markdown(_badge("✅ SQL Validated", _GREEN), unsafe_allow_html=True)
    else:
        st.markdown(_badge("❌ SQL Invalid", _RED), unsafe_allow_html=True)


def render_success_badge(label: str) -> None:
    """Render a generic success badge.

    Args:
        label: Badge text.
    """
    st.markdown(_badge(f"✅ {label}", _GREEN), unsafe_allow_html=True)


def render_info_badge(label: str) -> None:
    """Render a generic informational badge.

    Args:
        label: Badge text.
    """
    st.markdown(_badge(f"ℹ️ {label}", _BLUE), unsafe_allow_html=True)
