"""Governance facade used by AI pipeline orchestrators."""

import logging
import time
from typing import Optional

from src.common.config.settings import get_settings
from src.governance.exceptions import GuardrailViolationError
from src.governance.guardrails import GuardrailPipeline, InputGuardrail, OutputGuardrail
from src.governance.models import GovernanceTelemetry, GuardrailResult

logger = logging.getLogger("eakap.governance.service")


class GovernanceService:
    """Facade for input validation and output sanitization."""

    def __init__(
        self,
        input_pipeline: Optional[GuardrailPipeline] = None,
        output_pipeline: Optional[GuardrailPipeline] = None,
        strict_mode: Optional[bool] = None,
        enable_input_guardrails: Optional[bool] = None,
        enable_output_guardrails: Optional[bool] = None,
        enable_pii_redaction: Optional[bool] = None,
    ) -> None:
        settings = get_settings()
        self.strict_mode = settings.GUARDRAIL_STRICT_MODE if strict_mode is None else strict_mode
        self.enable_input_guardrails = (
            settings.ENABLE_INPUT_GUARDRAILS
            if enable_input_guardrails is None
            else enable_input_guardrails
        )
        self.enable_output_guardrails = (
            settings.ENABLE_OUTPUT_GUARDRAILS
            if enable_output_guardrails is None
            else enable_output_guardrails
        )
        self.enable_pii_redaction = (
            settings.ENABLE_PII_REDACTION
            if enable_pii_redaction is None
            else enable_pii_redaction
        )
        self.input_pipeline = input_pipeline or GuardrailPipeline([InputGuardrail()])
        self.output_pipeline = output_pipeline or GuardrailPipeline(
            [OutputGuardrail(enable_redaction=self.enable_pii_redaction)]
        )
        self.last_telemetry = GovernanceTelemetry(
            input_guardrails_enabled=self.enable_input_guardrails,
            output_guardrails_enabled=self.enable_output_guardrails,
            pii_redaction_enabled=self.enable_pii_redaction,
        )

    def validate_input(self, text: str) -> GuardrailResult:
        """Validate user input before pipeline execution."""
        start = time.perf_counter()
        if not self.enable_input_guardrails:
            result = GuardrailResult(
                guardrail_name="input_guardrails_disabled",
                is_allowed=True,
                sanitized_text=text,
            )
        else:
            result = self.input_pipeline.inspect(text)

        telemetry = self._base_telemetry()
        telemetry.input_violation_count = len(result.violations)
        telemetry.validation_time_ms = (time.perf_counter() - start) * 1_000
        telemetry.guardrails_executed = result.metadata.get("guardrails_executed", [])
        telemetry.status = "BLOCKED" if result.violations and self.strict_mode else "SUCCESS"
        self.last_telemetry = telemetry

        if result.violations and self.strict_mode:
            logger.warning("Input guardrail violation blocked request: %s", result.violations)
            raise GuardrailViolationError(message=f"Input guardrail violation: {result.violations}")
        return result

    def sanitize_output(self, text: str) -> GuardrailResult:
        """Sanitize generated output before response formatting."""
        start = time.perf_counter()
        if not self.enable_output_guardrails:
            result = GuardrailResult(
                guardrail_name="output_guardrails_disabled",
                is_allowed=True,
                sanitized_text=text,
            )
        else:
            result = self.output_pipeline.inspect(text)

        telemetry = self._base_telemetry()
        telemetry.output_violation_count = len(result.violations)
        telemetry.redaction_count = int(result.metadata.get("redaction_count", 0))
        telemetry.sanitization_time_ms = (time.perf_counter() - start) * 1_000
        telemetry.guardrails_executed = result.metadata.get("guardrails_executed", [])
        self.last_telemetry = telemetry
        return result

    def guardrail_registry(self) -> dict[str, list[str]]:
        """Return guardrails registered for input and output flows."""
        return {
            "input": self.input_pipeline.registry() if self.enable_input_guardrails else [],
            "output": self.output_pipeline.registry() if self.enable_output_guardrails else [],
        }

    def _base_telemetry(self) -> GovernanceTelemetry:
        return GovernanceTelemetry(
            input_guardrails_enabled=self.enable_input_guardrails,
            output_guardrails_enabled=self.enable_output_guardrails,
            pii_redaction_enabled=self.enable_pii_redaction,
        )
