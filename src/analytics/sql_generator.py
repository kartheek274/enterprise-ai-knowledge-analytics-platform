"""SQL generation service using the shared LLM abstraction."""

import logging
import re
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
        logger.info("Raw LLM SQL generation prompt:\n%s", prompt)
        try:
            sql, _, _ = self.llm_provider.generate(prompt=prompt, temperature=0.0)
            logger.info("Raw LLM SQL response: %s", sql)
            sanitized = self._strip_markdown(sql)
            logger.info("Extracted SQL after markdown stripping: %s", sanitized)
            if not sanitized:
                raise SQLGenerationError(message="LLM returned an empty SQL statement.")
            logger.info("SQL generated | model=%s | sql=%s", self.llm_provider.model_name, sanitized)
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
        logger.info("Raw LLM SQL generation prompt:\n%s", prompt)
        try:
            sql, prompt_tokens, completion_tokens = self.llm_provider.generate(
                prompt=prompt,
                temperature=0.0,
            )
            logger.info("Raw LLM SQL response: %s", sql)
            sanitized = self._strip_markdown(sql)
            logger.info("Extracted SQL after markdown stripping: %s", sanitized)
            return sanitized, prompt_tokens, completion_tokens
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
        """Strip markdown fences, thinking tags, and preamble from LLM text."""
        stripped = text.strip()

        # Remove thinking tags <think>...</think>
        stripped = re.sub(r"<think>.*?</think>", "", stripped, flags=re.DOTALL).strip()

        # Extract content from markdown code fences if present
        code_block_match = re.search(r"```(?:sql)?\s*(.*?)\s*```", stripped, re.DOTALL | re.IGNORECASE)
        if code_block_match:
            stripped = code_block_match.group(1).strip()

        # Extract statement starting from SELECT or WITH if LLM included preamble text
        select_match = re.search(r"\b(SELECT|WITH)\b.*", stripped, re.DOTALL | re.IGNORECASE)
        if select_match:
            stripped = select_match.group(0).strip()

        return stripped.rstrip(";").strip()
