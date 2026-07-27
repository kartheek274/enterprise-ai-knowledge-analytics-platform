import os
import pytest
from pathlib import Path
from src.common.config.settings import get_settings
from src.common.logging.logger import setup_logger
from src.common.errors.exceptions import (
    EAKAPBaseException,
    ConfigurationError,
    DatabaseConnectionError,
    SecurityViolationError,
    ValidationError,
    ResourceNotFoundError
)
from src.app.main import check_health

def test_settings_singleton_and_loading():
    """Verify that settings are loaded correctly as a singleton and are typed."""
    settings_1 = get_settings()
    settings_2 = get_settings()
    
    assert settings_1 is settings_2, "Settings must be a singleton instance"
    assert settings_1.APP_ENV in ["development", "production", "testing"]
    assert settings_1.DATABASE_URL.startswith("sqlite://")
    assert isinstance(settings_1.VECTOR_DB_PATH, Path)

def test_logger_writes_to_file():
    """Verify logger writes to log file and doesn't duplicate handlers."""
    logger = setup_logger("eakap.test")
    test_msg = "TEST LOG ENTRY - BACKBONE VERIFICATION"
    logger.info(test_msg)
    
    # Check if file has been created and contains log message
    log_file = Path(__file__).resolve().parent.parent / "logs" / "app.log"
    assert log_file.exists(), "Logger must write and persist logs to logs/app.log"
    
    log_content = log_file.read_text(encoding="utf-8")
    assert test_msg in log_content, "The test message must be written to log file"

def test_exception_chaining_and_types():
    """Verify exceptions raise properly, allow custom messages, and chain causes."""
    inner_exc = ValueError("Invalid database port")
    with pytest.raises(DatabaseConnectionError) as exc_info:
        raise DatabaseConnectionError("Failed to initialize SQLite pool", inner_exc)
        
    assert exc_info.value.message == "Failed to initialize SQLite pool"
    assert exc_info.value.original_exception is inner_exc
    assert exc_info.value.__cause__ is inner_exc

    with pytest.raises(ConfigurationError):
        raise ConfigurationError("Missing key")
        
    with pytest.raises(SecurityViolationError):
        raise SecurityViolationError("Unauthorized access")

    with pytest.raises(ValidationError):
        raise ValidationError("Input violates constraints")

    with pytest.raises(ResourceNotFoundError):
        raise ResourceNotFoundError("Guideline PDF missing")

def test_health_check_passes():
    """Verify that platform health check evaluates successfully."""
    from src.common.database.init_db import init_database
    init_database()
    is_healthy, details = check_health()
    assert is_healthy is True, f"Health check failed during test execution: {details}"
    assert details["configuration"]["status"] == "healthy"
    assert details["logging"]["status"] == "healthy"
    assert details["directories"]["paths"]["logs"] == "exists_and_writable"
    assert details["directories"]["paths"]["data"] == "exists_and_writable"
    assert details["runtime"]["status"] == "healthy"
