"""Base guardrail abstraction."""

from abc import ABC, abstractmethod

from src.governance.models import GuardrailResult


class BaseGuardrail(ABC):
    """Contract for text inspection and sanitization guardrails."""

    @abstractmethod
    def inspect(self, text: str) -> GuardrailResult:
        """Inspect text and return a structured guardrail result."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the guardrail identifier."""
