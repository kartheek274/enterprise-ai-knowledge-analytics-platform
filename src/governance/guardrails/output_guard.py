"""Output guardrail for PII/PHI sanitization."""

from src.governance.guardrails.base import BaseGuardrail
from src.governance.guardrails.pii_detector import PIIDetector
from src.governance.guardrails.pii_redactor import PIIRedactor
from src.governance.models import GuardrailResult, ViolationType


class OutputGuardrail(BaseGuardrail):
    """Detect and redact PII/PHI from generated model output."""

    def __init__(
        self,
        detector: PIIDetector | None = None,
        redactor: PIIRedactor | None = None,
        enable_redaction: bool = True,
    ) -> None:
        self.detector = detector or PIIDetector()
        self.redactor = redactor or PIIRedactor(self.detector)
        self.enable_redaction = enable_redaction

    @property
    def name(self) -> str:
        return "output_guardrail"

    def inspect(self, text: str) -> GuardrailResult:
        """Return sanitized output and PII metadata."""
        detection = self.detector.inspect(text)
        sanitized_text = text
        redaction_counts = {}
        if detection.violations and self.enable_redaction:
            sanitized_text, redaction_counts = self.redactor.redact(text)

        return GuardrailResult(
            guardrail_name=self.name,
            is_allowed=True,
            sanitized_text=sanitized_text,
            violations=[ViolationType.PII_DETECTED] if detection.violations else [],
            metadata={
                "findings": detection.metadata.get("findings", []),
                "redaction_counts": redaction_counts,
                "redaction_count": sum(redaction_counts.values()),
            },
        )
