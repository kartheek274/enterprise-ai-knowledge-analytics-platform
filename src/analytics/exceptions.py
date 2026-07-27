"""Analytics exception hierarchy."""

from src.common.errors.exceptions import EAKAPBaseException


class AnalyticsExecutionError(EAKAPBaseException):
    """Raised when the conversational BI pipeline fails."""


class SQLGenerationError(EAKAPBaseException):
    """Raised when SQL generation fails."""


class SQLValidationError(EAKAPBaseException):
    """Raised when generated SQL violates safety or schema rules."""


class SQLExecutionError(EAKAPBaseException):
    """Raised when validated SQL execution fails."""


class SchemaInspectionError(EAKAPBaseException):
    """Raised when analytics schema inspection fails."""
