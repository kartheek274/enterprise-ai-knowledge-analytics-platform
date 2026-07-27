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
        prompt_lower = prompt.lower()

        # 1. SQL Generation prompts
        is_sql_prompt = (
            "sql:" in prompt_lower
            or "schema:" in prompt_lower
            or "you generate safe sqlite sql" in prompt_lower
            or "sqlite syntax" in prompt_lower
        )
        if is_sql_prompt:
            if "claim" in prompt_lower:
                text = "SELECT claim_status, COUNT(claim_id) AS claim_count FROM claims GROUP BY claim_status"
            elif "financial" in prompt_lower or "paid" in prompt_lower:
                text = "SELECT record_id, claim_id, paid_amount FROM financial_records"
            elif "patient" in prompt_lower:
                text = "SELECT patient_id, first_name, last_name, state FROM patients"
            else:
                text = "SELECT claim_id, patient_id, claim_amount, claim_status FROM claims"

        # 2. Summary Generation prompts
        elif "summary:" in prompt_lower or "rows_json:" in prompt_lower or "execution_result" in prompt_lower:
            text = "The analysis retrieved matching records from the database."

        # 3. RAG Grounded QA prompts
        elif "context:" in prompt_lower:
            context_block = prompt.split("QUESTION:")[0] if "QUESTION:" in prompt else prompt
            parts = context_block.split("CONTEXT:")
            context_part = parts[1].strip() if len(parts) > 1 else ""
            if not context_part or "no matching context" in context_part.lower():
                text = "INSUFFICIENT_CONTEXT"
            else:
                text = self.fixed_response
        else:
            text = self.fixed_response

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
