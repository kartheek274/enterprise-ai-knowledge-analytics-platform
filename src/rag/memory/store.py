"""Storage abstractions for short-term conversational memory."""

import copy
import threading
from abc import ABC, abstractmethod
from typing import Dict, List

from src.rag.memory.exceptions import MemoryStoreError, SessionNotFoundError
from src.rag.memory.models import ConversationSession


class BaseMemoryStore(ABC):
    """Contract implemented by conversation memory stores."""

    @abstractmethod
    def save_session(self, session: ConversationSession) -> None:
        """Persist a conversation session."""

    @abstractmethod
    def get_session(self, session_id: str) -> ConversationSession:
        """Return a conversation session by identifier."""

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Delete a conversation session."""

    @abstractmethod
    def list_sessions(self) -> List[ConversationSession]:
        """Return all known sessions."""


class InMemorySessionStore(BaseMemoryStore):
    """Thread-safe dictionary-backed short-term memory store."""

    def __init__(self) -> None:
        self._sessions: Dict[str, ConversationSession] = {}
        self._lock = threading.RLock()

    def save_session(self, session: ConversationSession) -> None:
        """Persist a copy of the supplied session."""
        try:
            with self._lock:
                self._sessions[session.session_id] = copy.deepcopy(session)
        except Exception as exc:
            raise MemoryStoreError(
                message="Failed to save conversation session.",
                original_exception=exc,
            )

    def get_session(self, session_id: str) -> ConversationSession:
        """Return a copy of a stored session."""
        try:
            with self._lock:
                session = self._sessions.get(session_id)
                if session is None:
                    raise SessionNotFoundError(message=f"Session '{session_id}' was not found.")
                return copy.deepcopy(session)
        except SessionNotFoundError:
            raise
        except Exception as exc:
            raise MemoryStoreError(
                message="Failed to retrieve conversation session.",
                original_exception=exc,
            )

    def delete_session(self, session_id: str) -> None:
        """Delete a session when present."""
        try:
            with self._lock:
                self._sessions.pop(session_id, None)
        except Exception as exc:
            raise MemoryStoreError(
                message="Failed to delete conversation session.",
                original_exception=exc,
            )

    def list_sessions(self) -> List[ConversationSession]:
        """Return copies of all stored sessions."""
        try:
            with self._lock:
                return [copy.deepcopy(session) for session in self._sessions.values()]
        except Exception as exc:
            raise MemoryStoreError(
                message="Failed to list conversation sessions.",
                original_exception=exc,
            )
