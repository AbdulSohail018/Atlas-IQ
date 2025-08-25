"""
Logging configuration
"""

import logging
import sys
from typing import Any, Dict
import structlog
from structlog.typing import EventDict, Processor

from app.core.config import settings


def add_severity_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add severity level for Google Cloud Logging compatibility"""
    if method_name == "debug":
        event_dict["severity"] = "DEBUG"
    elif method_name == "info":
        event_dict["severity"] = "INFO"
    elif method_name == "warning":
        event_dict["severity"] = "WARNING"
    elif method_name == "error":
        event_dict["severity"] = "ERROR"
    elif method_name == "critical":
        event_dict["severity"] = "CRITICAL"
    return event_dict


def setup_logging() -> None:
    """Setup structured logging"""
    
    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper())
    )
    
    # Common processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        add_severity_level,
    ]
    
    # Add timestamp
    processors.append(structlog.processors.TimeStamper(fmt="iso"))
    
    # Choose renderer based on format
    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure uvicorn access log
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = []
    
    # Add correlation ID processor for request tracking
    structlog.contextvars.clear_contextvars()


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name) if name else structlog.get_logger()


class LoggerAdapter:
    """Adapter to provide context to loggers"""
    
    def __init__(self, logger: structlog.BoundLogger, extra: Dict[str, Any] = None):
        self.logger = logger
        self.extra = extra or {}
    
    def bind(self, **kwargs) -> structlog.BoundLogger:
        """Bind additional context to logger"""
        return self.logger.bind(**self.extra, **kwargs)
    
    def debug(self, msg: str, **kwargs) -> None:
        self.logger.debug(msg, **self.extra, **kwargs)
    
    def info(self, msg: str, **kwargs) -> None:
        self.logger.info(msg, **self.extra, **kwargs)
    
    def warning(self, msg: str, **kwargs) -> None:
        self.logger.warning(msg, **self.extra, **kwargs)
    
    def error(self, msg: str, **kwargs) -> None:
        self.logger.error(msg, **self.extra, **kwargs)
    
    def critical(self, msg: str, **kwargs) -> None:
        self.logger.critical(msg, **self.extra, **kwargs)