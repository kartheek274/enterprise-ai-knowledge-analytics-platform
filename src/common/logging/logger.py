import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from src.common.config.settings import get_settings

# Determine base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

def setup_logger(name: str = "eakap") -> logging.Logger:
    """
    Configure and return a structured logger instance.
    Prevents adding duplicate handlers to avoid duplicate log output.
    """
    logger = logging.getLogger(name)
    
    # Try to load log level from settings, fallback to INFO if configuration isn't loaded yet
    try:
        settings = get_settings()
        log_level_str = settings.LOG_LEVEL.upper()
    except Exception:
        log_level_str = "INFO"
        
    log_level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(log_level)

    # Avoid duplicate handlers if setup_logger is called multiple times
    if logger.handlers:
        return logger

    # Define structured format: timestamp | level | module.function:line | message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)

    # File Handler (Persistent logging)
    log_dir = BASE_DIR / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.log"
        
        # RotatingFileHandler prevents log file from growing infinitely in production
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB limit
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)
    except Exception as e:
        console_handler.flush()
        print(f"CRITICAL: Failed to initialize file logging in logs/ directory: {e}", file=sys.stderr)

    return logger
