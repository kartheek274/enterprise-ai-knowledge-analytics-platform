"""Conversation history formatting."""

from typing import List

from src.rag.memory.models import ChatTurn


class MemoryFormatter:
    """Convert ordered chat turns into prompt-ready conversation history."""

    ROLE_LABELS = {
        "user": "User",
        "assistant": "Assistant",
        "system": "System",
    }

    def format(self, turns: List[ChatTurn]) -> str:
        """Return chat history as alternating role-labeled text blocks."""
        lines = []
        for turn in turns:
            label = self.ROLE_LABELS.get(turn.role, turn.role.title())
            lines.append(f"{label}:\n{turn.content}")
        return "\n\n".join(lines)
