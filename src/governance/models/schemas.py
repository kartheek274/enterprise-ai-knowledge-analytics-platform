"""Governance domain models."""

from enum import StrEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ViolationType(StrEnum):
    """Supported governance violation categories."""

    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    INSTRUCTION_OVERRIDE = "instruction_override"
    COMMAND_INJECTION = "command_injection"
    PII_DETECTED = "pii_detected"


class GuardrailResult(BaseModel):
    """Structured result emitted by a guardrail inspection."""

    guardrail_name: str
    is_allowed: bool = True
    sanitized_text: Optional[str] = None
    violations: List[ViolationType] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GovernanceTelemetry(BaseModel):
    """Telemetry captured for governance validation and sanitization."""

    input_guardrails_enabled: bool = True
    output_guardrails_enabled: bool = True
    pii_redaction_enabled: bool = True
    input_violation_count: int = Field(default=0, ge=0)
    output_violation_count: int = Field(default=0, ge=0)
    redaction_count: int = Field(default=0, ge=0)
    guardrails_executed: List[str] = Field(default_factory=list)
    validation_time_ms: float = Field(default=0.0, ge=0.0)
    sanitization_time_ms: float = Field(default=0.0, ge=0.0)
    status: str = "SUCCESS"
