"""Deterministic LLM test double."""

from typing import Iterator, Optional, Tuple

from src.rag.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Mock provider used by unit tests and local health checks."""

    def __init__(self, fixed_response: Optional[str] = None) -> None:
        self.fixed_response = fixed_response or "Mock answer grounded in [1]."

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""
        return "mock"

    @property
    def model_name(self) -> str:
        """Return the mock model name."""
        return "mock-v1"

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> Tuple[str, int, int]:
        """Return a deterministic response without external calls."""
        text = "INSUFFICIENT_CONTEXT" if "CONTEXT:\n\n" in prompt else self.fixed_response
        return text, max(1, len(prompt) // 4), max(1, len(text) // 4)

    def stream_generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> Iterator[str]:
        """Yield deterministic response fragments."""
        text, _, _ = self.generate(prompt, max_tokens=max_tokens, temperature=temperature)
        for word in text.split():
            yield f"{word} "
