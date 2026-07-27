"""Session-level coordination for short-term conversational memory."""

import time
import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from src.common.config.settings import get_settings
from src.rag.memory.exceptions import MemoryCapacityExceededError, SessionNotFoundError
from src.rag.memory.formatter import MemoryFormatter
from src.rag.memory.models import ChatTurn, ConversationSession, MemoryConfig
from src.rag.memory.store import BaseMemoryStore, InMemorySessionStore
from src.rag.memory.telemetry import MemoryTelemetry


class SessionMemoryManager:
    """Manage short-term conversation sessions while delegating storage and formatting."""

    def __init__(
        self,
        store: Optional[BaseMemoryStore] = None,
        formatter: Optional[MemoryFormatter] = None,
        config: Optional[MemoryConfig] = None,
        token_counter: Optional[Callable[[str], int]] = None,
    ) -> None:
        settings = get_settings()
        self.store = store or InMemorySessionStore()
        self.formatter = formatter or MemoryFormatter()
        self.config = config or MemoryConfig(
            max_turns=settings.MAX_MEMORY_TURNS,
            max_tokens=settings.MAX_MEMORY_TOKENS,
            compression_strategy=settings.MEMORY_COMPRESSION_STRATEGY,
        )
        self.token_counter = token_counter or self._default_token_counter
        self.last_telemetry: Optional[MemoryTelemetry] = None
        self._lock = threading.RLock()

    def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
    ) -> ConversationSession:
        """Add one turn to a session, creating the session when needed."""
        with self._lock:
            session = self._get_or_create_session(session_id=session_id, user_id=user_id)
            turn = ChatTurn(
                role=role,
                content=content,
                token_count=self.token_counter(content),
            )
            session.turns.append(turn)
            session.updated_at = datetime.now(timezone.utc)
            trimmed = self._enforce_limits(session)
            self.store.save_session(session)
            self.last_telemetry = self._build_telemetry(session, trimmed_turns=trimmed)
            return session

    def get_formatted_history(self, session_id: str) -> str:
        """Return formatted conversation history for a session."""
        retrieval_start = time.perf_counter()
        try:
            session = self.store.get_session(session_id)
        except SessionNotFoundError:
            self.last_telemetry = MemoryTelemetry(session_id=session_id)
            return ""
        retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1_000

        formatting_start = time.perf_counter()
        formatted = self.formatter.format(session.turns)
        formatting_time_ms = (time.perf_counter() - formatting_start) * 1_000
        self.last_telemetry = self._build_telemetry(
            session,
            trimmed_turns=0,
            retrieval_time_ms=retrieval_time_ms,
            formatting_time_ms=formatting_time_ms,
        )
        return formatted

    def clear_session(self, session_id: str) -> None:
        """Delete a conversation session."""
        self.store.delete_session(session_id)
        self.last_telemetry = MemoryTelemetry(session_id=session_id)

    def get_session(self, session_id: str) -> ConversationSession:
        """Return a conversation session."""
        return self.store.get_session(session_id)

    def _get_or_create_session(self, session_id: str, user_id: Optional[str]) -> ConversationSession:
        try:
            session = self.store.get_session(session_id)
            if user_id and not session.user_id:
                session.user_id = user_id
            return session
        except SessionNotFoundError:
            return ConversationSession(
                session_id=session_id,
                user_id=user_id,
                max_tokens=self.config.max_tokens,
            )

    def _enforce_limits(self, session: ConversationSession) -> int:
        if self.config.compression_strategy != "trim_oldest":
            raise MemoryCapacityExceededError(
                message=f"Unsupported memory compression strategy: {self.config.compression_strategy}."
            )

        trimmed = 0
        while len(session.turns) > self.config.max_turns:
            session.turns.pop(0)
            trimmed += 1

        while session.total_tokens > self.config.max_tokens and session.turns:
            session.turns.pop(0)
            trimmed += 1

        if session.total_tokens > self.config.max_tokens:
            raise MemoryCapacityExceededError(message="Unable to enforce memory token capacity.")
        return trimmed

    def _build_telemetry(
        self,
        session: ConversationSession,
        trimmed_turns: int,
        retrieval_time_ms: float = 0.0,
        formatting_time_ms: float = 0.0,
    ) -> MemoryTelemetry:
        return MemoryTelemetry(
            session_id=session.session_id,
            total_turns=len(session.turns),
            total_tokens=session.total_tokens,
            trimmed_turns=trimmed_turns,
            retrieval_time_ms=retrieval_time_ms,
            formatting_time_ms=formatting_time_ms,
        )

    @staticmethod
    def _default_token_counter(text: str) -> int:
        return max(1, len(text) // 4)
