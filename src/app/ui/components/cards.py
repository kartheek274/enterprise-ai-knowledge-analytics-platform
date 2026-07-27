"""Enterprise-grade styled card components for the EAKAP Console.

Cards provide consistent visual containers across all tabs. They use
``st.markdown`` with scoped inline CSS so no external stylesheet is required.
"""

from __future__ import annotations

import streamlit as st


# --------------------------------------------------------------------------- #
# Palette constants (matches .streamlit/config.toml theme)                     #
# --------------------------------------------------------------------------- #
_ACCENT = "#6C63FF"
_BG_CARD = "rgba(108, 99, 255, 0.08)"
_BORDER = "rgba(108, 99, 255, 0.25)"
_TEXT_MUTED = "#a0a0b0"


def render_metric_card(
    title: str,
    value: str,
    delta: str | None = None,
    icon: str = "",
) -> None:
    """Render a bordered metric card with an optional delta line.

    Args:
        title: Card label displayed at the top in muted colour.
        value: Primary value displayed in large bold text.
        delta: Optional secondary line shown in accent colour.
        icon: Optional emoji prefix for the title.
    """
    delta_html = (
        f'<div style="font-size:0.8rem;color:{_ACCENT};margin-top:4px;">'
        f"{delta}</div>"
        if delta
        else ""
    )
    st.markdown(
        f"""
        <div style="background:{_BG_CARD};border:1px solid {_BORDER};
             border-radius:8px;padding:14px 18px;margin:4px 0;">
            <div style="font-size:0.78rem;color:{_TEXT_MUTED};
                        text-transform:uppercase;letter-spacing:0.05em;">
                {icon}&nbsp;{title}
            </div>
            <div style="font-size:1.5rem;font-weight:700;color:#fafafa;
                        margin-top:4px;">
                {value}
            </div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_card(title: str, icon: str = "") -> None:
    """Render a left-accented section header card.

    Args:
        title: Section label.
        icon: Optional emoji prefix.
    """
    st.markdown(
        f"""
        <div style="background:rgba(255,255,255,0.03);
             border-left:3px solid {_ACCENT};
             padding:8px 16px;margin:10px 0 6px 0;border-radius:0 6px 6px 0;">
            <strong style="color:#fafafa;">{icon}&nbsp;{title}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_info_card(title: str, body: str, icon: str = "ℹ️") -> None:
    """Render an informational card with a title and body text.

    Args:
        title: Bold title shown at the top.
        body:  Plain text or minimal HTML body content.
        icon:  Emoji prefix for the title.
    """
    st.markdown(
        f"""
        <div style="background:{_BG_CARD};border:1px solid {_BORDER};
             border-radius:8px;padding:14px 18px;margin:6px 0;">
            <div style="font-weight:600;color:#fafafa;margin-bottom:6px;">
                {icon}&nbsp;{title}
            </div>
            <div style="font-size:0.9rem;color:{_TEXT_MUTED};line-height:1.5;">
                {body}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
