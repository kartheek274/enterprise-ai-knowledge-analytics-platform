"""LLM provider factory and backward-compatible imports."""

from src.common.config.settings import get_settings
from src.common.errors.exceptions import LLMProviderError
from src.rag.llm.base import BaseLLMProvider
from src.rag.llm.mock import MockLLMProvider
from src.rag.llm.ollama import OllamaLLMProvider


def get_llm_provider() -> BaseLLMProvider:
    """Return the configured LLM provider without making a live generation call."""
    settings = get_settings()
    provider = getattr(settings, "LLM_PROVIDER", "ollama").lower()
    if settings.APP_ENV == "testing" or provider in {"mock", "testing"}:
        return MockLLMProvider()
    if provider == "ollama":
        return OllamaLLMProvider()
    raise LLMProviderError(message=f"Unknown LLM_PROVIDER value: '{provider}'.")


__all__ = ["BaseLLMProvider", "MockLLMProvider", "OllamaLLMProvider", "get_llm_provider"]
