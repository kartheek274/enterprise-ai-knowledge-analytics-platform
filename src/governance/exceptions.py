"""Governance exception hierarchy."""

from src.common.errors.exceptions import EAKAPBaseException


class GuardrailViolationError(EAKAPBaseException):
    """Raised when strict guardrail mode blocks unsafe content."""
