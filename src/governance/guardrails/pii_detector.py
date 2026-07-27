"""PII/PHI detection guardrail."""

import re
from typing import Dict, List, Pattern, Tuple

from src.governance.guardrails.base import BaseGuardrail
from src.governance.models import GuardrailResult, ViolationType


class PIIDetector(BaseGuardrail):
    """Detect common PII/PHI patterns in text."""

    PATTERNS: Dict[str, Pattern[str]] = {
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "mrn": re.compile(r"\bMRN[:\s-]*[A-Za-z0-9-]{3,}\b", re.IGNORECASE),
        "phone": re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "credit_card": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    }

    @property
    def name(self) -> str:
        return "pii_detector"

    def inspect(self, text: str) -> GuardrailResult:
        """Detect PII/PHI and return match counts by type."""
        findings = self.detect(text)
        return GuardrailResult(
            guardrail_name=self.name,
            is_allowed=not findings,
            sanitized_text=text,
            violations=[ViolationType.PII_DETECTED] if findings else [],
            metadata={
                "findings": [{"type": pii_type, "match": match} for pii_type, match in findings],
                "finding_count": len(findings),
            },
        )

    def detect(self, text: str) -> List[Tuple[str, str]]:
        """Return detected PII values as (type, match) tuples."""
        findings: List[Tuple[str, str]] = []
        for pii_type, pattern in self.PATTERNS.items():
            for match in pattern.findall(text):
                findings.append((pii_type, match))
        return findings
