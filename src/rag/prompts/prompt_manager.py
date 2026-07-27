"""Backward-compatible imports for the prompt manager package."""

from src.rag.prompts.manager import INSUFFICIENT_CONTEXT_SENTINEL, PromptManager
from src.rag.prompts.template import PromptTemplate

__all__ = ["INSUFFICIENT_CONTEXT_SENTINEL", "PromptManager", "PromptTemplate"]
