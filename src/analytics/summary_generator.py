"""Business summary generation for analytics results."""

import json
import logging

from src.analytics.exceptions import SQLGenerationError
from src.analytics.models import SQLExecutionResult
from src.rag.llm.base import BaseLLMProvider

logger = logging.getLogger("eakap.analytics.summary_generator")


class SummaryGenerator:
    """Generate concise business explanations from SQL results."""

    def __init__(self, llm_provider: BaseLLMProvider) -> None:
        self.llm_provider = llm_provider

    def generate_summary(self, question: str, execution_result: SQLExecutionResult) -> str:
        """Return a concise natural-language summary using only result rows."""
        prompt = (
            "You summarize SQL analytics results for healthcare operations.\n"
            "Use only the provided question and result rows. Be concise.\n\n"
            f"QUESTION:\n{question}\n\n"
            f"ROW_COUNT:\n{execution_result.row_count}\n\n"
            f"ROWS_JSON:\n{json.dumps(execution_result.rows[:20], default=str)}\n\n"
            "SUMMARY:"
        )
        try:
            summary, _, _ = self.llm_provider.generate(prompt=prompt, temperature=0.0)
            text = summary.strip()
            if not text:
                return "No business summary was generated."
            logger.info("Analytics summary generated | model=%s", self.llm_provider.model_name)
            return text
        except Exception as exc:
            raise SQLGenerationError(
                message="Failed to generate analytics summary.",
                original_exception=exc,
            )
