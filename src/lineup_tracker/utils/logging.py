"""
Structured logging framework for LineupTracker.

Provides JSON-structured logging with context management, correlation IDs,
and proper log aggregation support for production environments.
"""

import logging
import json
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Union
from contextvars import ContextVar
from pathlib import Path


# Context variables for correlation tracking
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


class StructuredFormatter(logging.Formatter):
    """
    JSON structured logging formatter.
    
    Formats log records as JSON with structured fields for easy parsing
    by log aggregation systems like ELK, Splunk, or CloudWatch.
    """
    
    def __init__(self, include_extra_fields: bool = True):
        super().__init__()
        self.include_extra_fields = include_extra_fields
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log entry structure
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'process': record.process
        }
        
        # Add correlation ID if available
        corr_id = correlation_id.get()
        if corr_id:
            log_entry['correlation_id'] = corr_id
        
        # Add request context if available
        context = request_context.get()
        if context:
            log_entry['context'] = context
        
        # Add exception information if present
        if record.exc_info and record.exc_info != (None, None, None):
            exc_type, exc_value, exc_traceback = record.exc_info
            if exc_type is not None:
                log_entry['exception'] = {
                    'type': exc_type.__name__,
                    'message': str(exc_value) if exc_value else None,
                    'traceback': self.formatException(record.exc_info)
                }
        
        # Add extra fields from record
        if self.include_extra_fields and hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add custom fields from record attributes
        extra_attrs = {
            k: v for k, v in record.__dict__.items()
            if k not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'getMessage',
                'message', 'extra_fields'
            }
        }
        
        if extra_attrs:
            log_entry['extra'] = extra_attrs
        
        return json.dumps(log_entry, default=self._json_serializer)
    
    def _json_serializer(self, obj: Any) -> str:
        """Custom JSON serializer for non-serializable objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return str(obj)
        else:
            return str(obj)


class ContextLogger:
    """
    Context-aware logger that maintains correlation IDs and request context.
    
    Provides structured logging with automatic context propagation
    and correlation ID tracking for distributed tracing.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with context support."""
        if self.logger.isEnabledFor(level):
            record = self.logger.makeRecord(
                self.logger.name, level, '', 0, message, (), None
            )
            
            # Add extra fields
            if kwargs:
                record.extra_fields = kwargs
            
            self.logger.handle(record)


class LoggerManager:
    """
    Manages logger configuration and provides factory methods.
    
    Centralizes logger setup with consistent formatting and handlers
    across the entire application.
    """
    
    _configured = False
    _loggers: Dict[str, ContextLogger] = {}
    
    @classmethod
    def configure_logging(
        cls,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        enable_console: bool = True,
        structured_format: bool = True
    ) -> None:
        """
        Configure application-wide logging.
        
        Args:
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional file path for log output
            enable_console: Whether to log to console
            structured_format: Whether to use structured JSON format
        """
        if cls._configured:
            return
        
        # Set root logger level
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        if structured_format:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_level.upper()))
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        cls._configured = True
    
    @classmethod
    def get_logger(cls, name: str) -> ContextLogger:
        """
        Get a context-aware logger for the given name.
        
        Args:
            name: Logger name (typically __name__)
            
        Returns:
            ContextLogger instance
        """
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = ContextLogger(logger)
        
        return cls._loggers[name]
    
    @classmethod
    def reset(cls):
        """Reset logger configuration (useful for testing)."""
        cls._configured = False
        cls._loggers.clear()


class CorrelationContext:
    """
    Context manager for correlation ID and request context.
    
    Automatically generates and manages correlation IDs for tracking
    requests and operations across the application.
    """
    
    def __init__(self, correlation_id_value: Optional[str] = None, **context_data):
        self.correlation_id_value = correlation_id_value or str(uuid.uuid4())
        self.context_data = context_data
        self.old_correlation_id = None
        self.old_context = None
    
    def __enter__(self):
        """Enter context and set correlation ID."""
        self.old_correlation_id = correlation_id.get()
        self.old_context = request_context.get()
        
        correlation_id.set(self.correlation_id_value)
        request_context.set(self.context_data)
        
        return self.correlation_id_value
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore previous values."""
        correlation_id.set(self.old_correlation_id)
        request_context.set(self.old_context)


def log_with_context(logger: Union[logging.Logger, ContextLogger], level: str, message: str, **context):
    """
    Log with additional context fields.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context fields
    """
    if isinstance(logger, ContextLogger):
        getattr(logger, level.lower())(message, **context)
    else:
        # Handle standard logger
        log_level = getattr(logging, level.upper())
        if logger.isEnabledFor(log_level):
            record = logger.makeRecord(
                logger.name, log_level, '', 0, message, (), None
            )
            record.extra_fields = context
            logger.handle(record)


def log_function_call(func_name: str, **kwargs):
    """
    Decorator for logging function calls with parameters.
    
    Args:
        func_name: Function name to log
        **kwargs: Additional context
    """
    def decorator(func):
        def wrapper(*args, **kwargs_inner):
            logger = LoggerManager.get_logger(func.__module__)
            
            with CorrelationContext(function=func_name, **kwargs):
                logger.debug(
                    f"Calling {func_name}",
                    args_count=len(args),
                    kwargs_count=len(kwargs_inner)
                )
                
                try:
                    result = func(*args, **kwargs_inner)
                    logger.debug(f"Completed {func_name} successfully")
                    return result
                except Exception as e:
                    logger.error(
                        f"Error in {func_name}: {str(e)}",
                        exception_type=type(e).__name__
                    )
                    raise
        
        return wrapper
    return decorator


def log_performance(operation_name: str):
    """
    Decorator for logging performance metrics.
    
    Args:
        operation_name: Name of the operation being measured
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            
            logger = LoggerManager.get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"Performance: {operation_name} completed",
                    duration_seconds=duration,
                    operation=operation_name
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"Performance: {operation_name} failed",
                    duration_seconds=duration,
                    operation=operation_name,
                    error=str(e)
                )
                raise
        
        return wrapper
    return decorator


# Convenience functions
def get_logger(name: str) -> ContextLogger:
    """Get a context-aware logger."""
    return LoggerManager.get_logger(name)


def configure_logging(**kwargs):
    """Configure application logging."""
    LoggerManager.configure_logging(**kwargs)


def create_correlation_context(**context):
    """Create a correlation context."""
    return CorrelationContext(**context)


# Pre-configured logger for this module
logger = get_logger(__name__)
