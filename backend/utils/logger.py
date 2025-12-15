"""
Structured logging configuration for Nebula Translate backend.
"""

import sys
import logging
from loguru import logger
from pythonjsonlogger import jsonlogger
from config import settings


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages and redirect to loguru.
    """

    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging():
    """Configure structured logging for the application."""

    # Remove default loguru handler
    logger.remove()

    # Configure format based on environment
    if settings.environment == "production":
        # JSON structured logs for production
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level> | "
            "{extra}"
        )
    else:
        # Human-readable logs for development
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

    # Add handler to stderr
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=settings.debug,
    )

    # Add file handler for production
    if settings.environment == "production":
        logger.add(
            "logs/nebula-translate.log",
            format=log_format,
            level="INFO",
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            serialize=True,  # JSON output
        )

    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Set levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("aiortc").setLevel(logging.WARNING)

    logger.info(f"Logging configured for {settings.environment} environment")


def get_logger(name: str):
    """Get a logger instance with a specific name."""
    return logger.bind(module=name)


# Session-aware logging context
class SessionLogger:
    """Logger with session context."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = logger.bind(session_id=session_id)

    def debug(self, message: str, **kwargs):
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs):
        self.logger.critical(message, **kwargs)
