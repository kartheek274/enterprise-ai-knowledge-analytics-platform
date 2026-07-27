"""UI State Manager — sole gateway to ``st.session_state`` for EAKAP Console.

**Design contract**: No other UI module is permitted to read from or write to
``st.session_state`` directly. All session state operations must be routed
through this class.

This encapsulation makes session state:

- Testable without a running Streamlit server (mock ``st`` at import time).
- Easy to audit — every key lives in one place.
- Safe from accidental key collisions across tabs.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

import streamlit as st

logger = logging.getLogger("eakap.app.ui.state")

# --------------------------------------------------------------------------- #
# Session state keys — centralised here; never hard-coded elsewhere             #
# --------------------------------------------------------------------------- #
_KEY_SESSION_ID = "current_session_id"
_KEY_CHAT_HISTORY = "chat_history"
_KEY_TELEMETRY = "telemetry_logs"
_KEY_ACTIVE_TAB = "active_tab"

DEFAULT_TAB = "🧠 Knowledge Assistant"


class UIStateManager:
    """Encapsulate all Streamlit session state access for the EAKAP Console.

    Example::

        state = UIStateManager()
        state.initialize()                   # call once per script run
        state.add_chat_turn("user", "Hello")
        history = state.get_chat_history()
        state.clear_session()
    """

    # ------------------------------------------------------------------ #
    # Lifecycle                                                             #
    # ------------------------------------------------------------------ #

    def initialize(self) -> None:
        """Safely seed all required session state keys with type-safe defaults.

        Idempotent — safe to call on every Streamlit script re-run. Existing
        values are never overwritten.
        """
        if _KEY_SESSION_ID not in st.session_state:
            st.session_state[_KEY_SESSION_ID] = str(uuid.uuid4())
        if _KEY_CHAT_HISTORY not in st.session_state:
            st.session_state[_KEY_CHAT_HISTORY] = []
        if _KEY_TELEMETRY not in st.session_state:
            st.session_state[_KEY_TELEMETRY] = []
        if _KEY_ACTIVE_TAB not in st.session_state:
            st.session_state[_KEY_ACTIVE_TAB] = DEFAULT_TAB

    # ------------------------------------------------------------------ #
    # Session ID                                                            #
    # ------------------------------------------------------------------ #

    def get_session_id(self) -> str:
        """Return the current active conversation session ID.

        Falls back to generating a fresh UUID if the key is absent, which can
        happen if ``initialize()`` has not been called yet.
        """
        return str(st.session_state.get(_KEY_SESSION_ID, str(uuid.uuid4())))

    def set_session_id(self, session_id: str) -> None:
        """Override the active session ID.

        Args:
            session_id: New session identifier (custom or UUID).
        """
        st.session_state[_KEY_SESSION_ID] = session_id
        logger.info("Session ID changed to: %s", session_id)

    # ------------------------------------------------------------------ #
    # Chat history                                                          #
    # ------------------------------------------------------------------ #

    def add_chat_turn(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a conversation turn to the chat history.

        Args:
            role:     ``"user"`` or ``"assistant"``.
            content:  The turn text.
            metadata: Optional structured payload (telemetry, citations, etc.).
        """
        turn: Dict[str, Any] = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }
        st.session_state[_KEY_CHAT_HISTORY].append(turn)

    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Return a snapshot of the current chat history.

        Returns:
            List of turn dicts, each with ``role``, ``content``, ``metadata``.
        """
        return list(st.session_state.get(_KEY_CHAT_HISTORY, []))

    # ------------------------------------------------------------------ #
    # Telemetry                                                             #
    # ------------------------------------------------------------------ #

    def append_telemetry(self, entry: Dict[str, Any]) -> None:
        """Append a telemetry event to the session log.

        Args:
            entry: Flat dict of telemetry fields (source, latency, PII flags…).
        """
        st.session_state[_KEY_TELEMETRY].append(entry)

    def get_telemetry_logs(self) -> List[Dict[str, Any]]:
        """Return all accumulated telemetry entries for this session.

        Returns:
            List of event dicts ordered by insertion time.
        """
        return list(st.session_state.get(_KEY_TELEMETRY, []))

    # ------------------------------------------------------------------ #
    # Active tab                                                            #
    # ------------------------------------------------------------------ #

    def get_active_tab(self) -> str:
        """Return the name of the currently active console tab."""
        return str(st.session_state.get(_KEY_ACTIVE_TAB, DEFAULT_TAB))

    def set_active_tab(self, tab: str) -> None:
        """Set the active tab name.

        Args:
            tab: Full tab label including emoji prefix.
        """
        st.session_state[_KEY_ACTIVE_TAB] = tab

    # ------------------------------------------------------------------ #
    # Session management                                                    #
    # ------------------------------------------------------------------ #

    def clear_session(self) -> None:
        """Reset conversation state and generate a fresh session ID.

        Clears chat history and telemetry logs. Sets a new UUID session ID.
        """
        st.session_state[_KEY_SESSION_ID] = str(uuid.uuid4())
        st.session_state[_KEY_CHAT_HISTORY] = []
        st.session_state[_KEY_TELEMETRY] = []
        logger.info("Session cleared. New session ID assigned.")
