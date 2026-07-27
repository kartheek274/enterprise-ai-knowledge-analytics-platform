"""Domain models for short-term conversational memory."""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ChatTurn(BaseModel):
    """Single user or assistant message retained in short-term memory."""

    turn_id: str = Field(default_factory=lambda: str(uuid4()))
    role: str
    content: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    token_count: int = Field(default=0, ge=0)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        """Accept only supported chat roles."""
        normalized = value.strip().lower()
        if normalized not in {"user", "assistant", "system"}:
            raise ValueError("role must be one of: user, assistant, system.")
        return normalized

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        """Reject empty or whitespace-only message content."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("content must be a non-empty string.")
        return stripped


class ConversationSession(BaseModel):
    """Short-term memory session containing ordered chat turns."""

    session_id: str
    user_id: Optional[str] = None
    turns: List[ChatTurn] = Field(default_factory=list)
    max_tokens: int = Field(default=2000, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_tokens(self) -> int:
        """Return total approximate tokens across all turns."""
        return sum(turn.token_count for turn in self.turns)


class MemoryConfig(BaseModel):
    """Configuration for short-term conversation memory behavior."""

    max_turns: int = Field(default=20, ge=1)
    max_tokens: int = Field(default=2000, ge=1)
    compression_strategy: str = "trim_oldest"
