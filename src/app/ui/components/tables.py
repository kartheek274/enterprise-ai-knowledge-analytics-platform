"""Formatted table display helpers for the EAKAP Enterprise Console.

Provides consistent DataFrame rendering and key-value table utilities
used across all console tabs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st

_SENSITIVE_PATTERNS = [
    "KEY",
    "SECRET",
    "PASSWORD",
    "TOKEN",
    "API_KEY",
    "ACCESS_KEY",
    "CLIENT_SECRET",
    "PRIVATE_KEY",
    "CONNECTION_STRING",
]


def render_citations_table(chunks: List[Any]) -> None:
    """Render a RAG citation table from a list of ``RetrievedChunk`` objects.

    Accepts any objects that expose ``source_filename``, ``chunk_index``,
    ``similarity_score``, and ``content`` attributes, including both the real
    ``RetrievedChunk`` domain model and lightweight test stubs.

    Args:
        chunks: Retrieved document fragments to display.
    """
    import pandas as pd

    if not chunks:
        st.info("No citations available for this response.")
        return

    rows = []
    for chunk in chunks:
        preview = chunk.content
        if len(preview) > 100:
            preview = preview[:97] + "..."
        rows.append(
            {
                "Source File": chunk.source_filename,
                "Chunk #": chunk.chunk_index,
                "Score": f"{chunk.similarity_score:.3f}",
                "Content Preview": preview,
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_dict_table(
    data: Dict[str, Any],
    title: Optional[str] = None,
    redact_keys: Optional[List[str]] = None,
) -> None:
    """Render a key-value dictionary as a two-column DataFrame.

    Automatically masks sensitive configuration keys containing keywords such as
    KEY, SECRET, PASSWORD, TOKEN, API_KEY, ACCESS_KEY, CLIENT_SECRET, PRIVATE_KEY, CONNECTION_STRING.

    Args:
        data:        Key-value pairs to display.
        title:       Optional caption shown above the table.
        redact_keys: Additional keys whose values should be masked.
    """
    import pandas as pd

    redact_keys = [k.upper() for k in (redact_keys or [])]

    if title:
        st.caption(title)

    if not data:
        st.info("No data to display.")
        return

    rows = []
    for k, v in data.items():
        k_upper = str(k).upper()
        is_sensitive = (
            k_upper in redact_keys
            or any(pattern in k_upper for pattern in _SENSITIVE_PATTERNS)
        )
        rows.append(
            {
                "Setting": k,
                "Value": "[REDACTED]" if is_sensitive else str(v),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_telemetry_table(logs: List[Dict[str, Any]]) -> None:
    """Render a list of telemetry log dicts as a DataFrame.

    Args:
        logs: Accumulated telemetry entries from ``UIStateManager``.
    """
    import pandas as pd

    if not logs:
        st.info("No telemetry recorded yet. Run some queries to generate data.")
        return

    df = pd.DataFrame(logs)
    st.dataframe(df, use_container_width=True, hide_index=True)
