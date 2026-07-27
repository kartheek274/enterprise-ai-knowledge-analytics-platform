"""Automatic chart selection for Conversational BI results.

Inspects the column types and value shapes in the result set and selects the
most appropriate Streamlit visualization.

Chart selection heuristics:
1. Single numeric value (1 row, 1 numeric col) -> st.metric
2. Datetime + numeric -> st.line_chart
3. Categorical + numeric -> st.bar_chart
4. Multiple numeric columns (no index) -> dataframe fallback
5. Unsupported datasets -> dataframe fallback (no chart)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import streamlit as st

logger = logging.getLogger("eakap.app.ui.charts")


def auto_chart(rows: List[Dict[str, Any]], columns: List[str]) -> None:
    """Auto-select and render the most appropriate chart for query results.

    Args:
        rows:    SQL execution result rows as a list of dicts.
        columns: Ordered column names from the execution result.
    """
    import pandas as pd

    if not rows or not columns:
        return

    df = pd.DataFrame(rows, columns=columns)

    # Detect single numeric value (1 row, 1 numeric column)
    if len(df) == 1:
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        if len(numeric_cols) == 1 and len(columns) == 1:
            col_name = numeric_cols[0]
            val = df.iloc[0][col_name]
            st.markdown("**📈 Key Metric**")
            st.metric(label=col_name.replace("_", " ").title(), value=f"{val:,}" if isinstance(val, (int, float)) else str(val))
            return

    # Convert date/time string columns to datetime if possible
    dt_cols: List[str] = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            dt_cols.append(col)
        elif df[col].dtype == object or df[col].dtype == str:
            # Check if column name or values look like dates
            col_lower = str(col).lower()
            if any(term in col_lower for term in ["date", "time", "month", "year", "day"]):
                try:
                    df[col] = pd.to_datetime(df[col])
                    dt_cols.append(col)
                except Exception:
                    pass

    numeric_cols: List[str] = df.select_dtypes(include="number").columns.tolist()
    categorical_cols: List[str] = [c for c in df.select_dtypes(exclude="number").columns.tolist() if c not in dt_cols]

    if not numeric_cols:
        logger.debug("auto_chart: no numeric columns — skipping chart.")
        return

    try:
        # Heuristic 1: Datetime + numeric -> line chart
        if dt_cols:
            st.markdown("**📈 Trend Chart**")
            chart_df = df.set_index(dt_cols[0])[numeric_cols]
            st.line_chart(chart_df, use_container_width=True)
            return

        # Heuristic 2: Categorical + numeric -> bar chart
        if categorical_cols:
            st.markdown("**📈 Bar Chart**")
            chart_df = df.set_index(categorical_cols[0])[numeric_cols]
            st.bar_chart(chart_df, use_container_width=True)
            return

        # Heuristic 3: Multiple numeric columns without index -> dataframe display
        if len(numeric_cols) >= 2:
            logger.debug("auto_chart: multiple numeric columns without index category — displaying as dataframe.")
            return

        # Heuristic 4: Single numeric column with multiple rows -> bar chart
        if len(numeric_cols) == 1 and len(df) > 1:
            st.markdown("**📈 Distribution Chart**")
            st.bar_chart(df[numeric_cols], use_container_width=True)
            return

    except Exception as exc:
        logger.warning("auto_chart failed to render: %s", exc)
        st.caption(f"Chart unavailable: {exc}")
