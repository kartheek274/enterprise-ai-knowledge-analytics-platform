"""Conversation memory exception hierarchy."""

from src.common.errors.exceptions import EAKAPBaseException


class MemoryStoreError(EAKAPBaseException):
    """Raised when a memory store operation fails."""


class SessionNotFoundError(EAKAPBaseException):
    """Raised when a requested conversation session does not exist."""


class MemoryCapacityExceededError(EAKAPBaseException):
    """Raised when memory limits cannot be enforced safely."""
