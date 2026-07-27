"""Reusable guardrail pipeline."""

from typing import Iterable, List

from src.governance.guardrails.base import BaseGuardrail
from src.governance.models import GuardrailResult


class GuardrailPipeline:
    """Execute registered guardrails in sequence and aggregate results."""

    def __init__(self, guardrails: Iterable[BaseGuardrail]) -> None:
        self.guardrails: List[BaseGuardrail] = list(guardrails)

    def inspect(self, text: str) -> GuardrailResult:
        """Run all guardrails and return an aggregate result."""
        current_text = text
        aggregate = GuardrailResult(
            guardrail_name="guardrail_pipeline",
            is_allowed=True,
            sanitized_text=text,
            metadata={"results": [], "guardrails_executed": []},
        )

        for guardrail in self.guardrails:
            result = guardrail.inspect(current_text)
            current_text = result.sanitized_text if result.sanitized_text is not None else current_text
            aggregate.is_allowed = aggregate.is_allowed and result.is_allowed
            aggregate.violations.extend(result.violations)
            aggregate.metadata["results"].append(result.model_dump())
            aggregate.metadata["guardrails_executed"].append(guardrail.name)

        aggregate.sanitized_text = current_text
        aggregate.metadata["violation_count"] = len(aggregate.violations)
        aggregate.metadata["redaction_count"] = sum(
            int(result.get("metadata", {}).get("redaction_count", 0))
            for result in aggregate.metadata["results"]
        )
        return aggregate

    def registry(self) -> List[str]:
        """Return registered guardrail names."""
        return [guardrail.name for guardrail in self.guardrails]
