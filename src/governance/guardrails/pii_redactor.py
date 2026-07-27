"""PII/PHI redaction utility."""

from typing import Dict, Tuple

from src.governance.guardrails.pii_detector import PIIDetector


class PIIRedactor:
    """Mask supported PII/PHI values in text."""

    REPLACEMENTS: Dict[str, str] = {
        "ssn": "[SSN]",
        "mrn": "[MRN]",
        "phone": "[PHONE]",
        "email": "[EMAIL]",
        "credit_card": "[CREDIT_CARD]",
    }

    def __init__(self, detector: PIIDetector | None = None) -> None:
        self.detector = detector or PIIDetector()

    def redact(self, text: str) -> Tuple[str, Dict[str, int]]:
        """Return redacted text and counts by PII type."""
        sanitized = text
        counts: Dict[str, int] = {}
        for pii_type, pattern in self.detector.PATTERNS.items():
            sanitized, count = pattern.subn(self.REPLACEMENTS[pii_type], sanitized)
            if count:
                counts[pii_type] = count
        return sanitized, counts
