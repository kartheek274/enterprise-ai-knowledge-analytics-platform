"""Input guardrail for prompt and command injection patterns."""

import re
from typing import Dict, List, Pattern

from src.governance.guardrails.base import BaseGuardrail
from src.governance.models import GuardrailResult, ViolationType


class InputGuardrail(BaseGuardrail):
    """Detect unsafe input patterns before AI pipeline execution."""

    PATTERNS: Dict[ViolationType, List[Pattern[str]]] = {
        ViolationType.PROMPT_INJECTION: [
            re.compile(r"\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b", re.IGNORECASE),
            re.compile(r"\bdisregard\s+(all\s+)?(previous|prior|above)\s+instructions\b", re.IGNORECASE),
        ],
        ViolationType.JAILBREAK: [
            re.compile(r"\bDAN\b", re.IGNORECASE),
            re.compile(r"\bjailbreak\b", re.IGNORECASE),
            re.compile(r"\bdeveloper mode\b", re.IGNORECASE),
        ],
        ViolationType.INSTRUCTION_OVERRIDE: [
            re.compile(r"\bsystem\s*:\s*", re.IGNORECASE),
            re.compile(r"\byou are now\b", re.IGNORECASE),
            re.compile(r"\boverride\b.*\binstruction", re.IGNORECASE),
        ],
        ViolationType.COMMAND_INJECTION: [
            re.compile(r"(\||&&|\|\|)\s*(rm|del|curl|wget|powershell|cmd|bash)\b", re.IGNORECASE),
            re.compile(r"\b(rm\s+-rf|del\s+/[fsq]|format\s+[a-z]:)", re.IGNORECASE),
        ],
    }

    @property
    def name(self) -> str:
        return "input_guardrail"

    def inspect(self, text: str) -> GuardrailResult:
        """Return violations for prompt, jailbreak, override, and command patterns."""
        violations: List[ViolationType] = []
        matched_patterns: List[str] = []
        for violation_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if pattern.search(text):
                    violations.append(violation_type)
                    matched_patterns.append(pattern.pattern)
                    break

        return GuardrailResult(
            guardrail_name=self.name,
            is_allowed=not violations,
            sanitized_text=text,
            violations=violations,
            metadata={"matched_patterns": matched_patterns},
        )
