"""SQL generation service using the shared LLM abstraction."""

import logging
from typing import Tuple

from src.analytics.exceptions import SQLGenerationError
from src.rag.llm.base import BaseLLMProvider

logger = logging.getLogger("eakap.analytics.sql_generator")


class SQLGenerator:
    """Generate SQLite SQL from a business question and schema context."""

    def __init__(self, llm_provider: BaseLLMProvider) -> None:
        self.llm_provider = llm_provider

    def generate_sql(self, question: str, schema_context: str) -> str:
        """Generate candidate SQL only, with no markdown or explanatory text."""
        prompt = self._build_prompt(question=question, schema_context=schema_context)
        try:
            sql, _, _ = self.llm_provider.generate(prompt=prompt, temperature=0.0)
            sanitized = self._strip_markdown(sql)
            if not sanitized:
                raise SQLGenerationError(message="LLM returned an empty SQL statement.")
            logger.info("SQL generated | model=%s", self.llm_provider.model_name)
            return sanitized
        except SQLGenerationError:
            raise
        except Exception as exc:
            raise SQLGenerationError(
                message="Failed to generate SQL from analytics question.",
                original_exception=exc,
            )

    def generate_sql_with_usage(self, question: str, schema_context: str) -> Tuple[str, int, int]:
        """Generate SQL and return provider token usage for future telemetry consumers."""
        prompt = self._build_prompt(question=question, schema_context=schema_context)
        try:
            sql, prompt_tokens, completion_tokens = self.llm_provider.generate(
                prompt=prompt,
                temperature=0.0,
            )
            return self._strip_markdown(sql), prompt_tokens, completion_tokens
        except Exception as exc:
            raise SQLGenerationError(
                message="Failed to generate SQL from analytics question.",
                original_exception=exc,
            )

    @staticmethod
    def _build_prompt(question: str, schema_context: str) -> str:
        return (
            "You generate safe SQLite SQL for enterprise healthcare analytics.\n"
            "Rules:\n"
            "- Use SQLite syntax only.\n"
            "- Use only the tables and columns in the supplied schema.\n"
            "- Never invent tables or columns.\n"
            "- Use explicit JOINs.\n"
            "- Never use SELECT * unless the user explicitly asks for all columns.\n"
            "- Qualify ambiguous columns with table names or aliases.\n"
            "- Return SQL only. No markdown. No explanations.\n\n"
            f"SCHEMA:\n{schema_context}\n\n"
            f"QUESTION:\n{question}\n\n"
            "SQL:"
        )

    @staticmethod
    def _strip_markdown(text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`").strip()
            if stripped.lower().startswith("sql"):
                stripped = stripped[3:].strip()
        return stripped.strip()
