"""LLM provider abstraction for query generation."""

from abc import ABC, abstractmethod
from typing import Iterator, Tuple


class BaseLLMProvider(ABC):
    """Interface contract implemented by all LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> Tuple[str, int, int]:
        """Return generated text, prompt token count, and completion token count."""

    @abstractmethod
    def stream_generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> Iterator[str]:
        """Yield generated text fragments."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the active model name."""
