from typing import Optional

class EAKAPBaseException(Exception):
    """
    Base exception class for all errors in the EAKAP platform.
    Ensures structured logging of internal platform issues and provides
    consistent handling across multiple modules.
    """
    def __init__(self, message: str, original_exception: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.message = message
        self.original_exception = original_exception
        if original_exception:
            self.__cause__ = original_exception

    def __str__(self) -> str:
        if self.original_exception:
            return f"{self.message} (Caused by: {repr(self.original_exception)})"
        return self.message

class ConfigurationError(EAKAPBaseException):
    """Raised when configuration loading, validation, or parsing fails."""
    pass

class DatabaseConnectionError(EAKAPBaseException):
    """Raised when connection to SQLite, Snowflake, or Vector database fails."""
    pass

class SecurityViolationError(EAKAPBaseException):
    """Raised when authentication, authorization, or safety checks fail."""
    pass

class ValidationError(EAKAPBaseException):
    """Raised when business logic data validation fails."""
    pass

class ResourceNotFoundError(EAKAPBaseException):
    """Raised when a requested resource (file, record, prompt) does not exist."""
    pass

class LLMProviderError(EAKAPBaseException):
    """Raised when an LLM provider fails to generate a response (network, model, or timeout errors)."""
    pass

class RetrievalError(EAKAPBaseException):
    """Raised when semantic retrieval fails due to embedding or vector search errors."""
    pass
