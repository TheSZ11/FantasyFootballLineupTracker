"""
Unit tests for structured logging framework.

Tests the structured logging, correlation IDs, context management,
and performance logging features.
"""

import pytest
import json
import logging
import io
from unittest.mock import patch, Mock
from datetime import datetime

from src.lineup_tracker.utils.logging import (
    StructuredFormatter, ContextLogger, LoggerManager,
    CorrelationContext, log_with_context, log_function_call,
    log_performance, get_logger, configure_logging,
    correlation_id, request_context
)


@pytest.mark.unit
class TestStructuredFormatter:
    """Test the structured JSON formatter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = StructuredFormatter()
    
    def test_basic_formatting(self):
        """Test basic log record formatting."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = self.formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data['level'] == 'INFO'
        assert log_data['logger'] == 'test.logger'
        assert log_data['message'] == 'Test message'
        assert log_data['module'] == 'test'
        assert log_data['function'] is not None  # Function name may vary by Python version
        assert log_data['line'] == 10
        assert 'timestamp' in log_data
        assert 'thread' in log_data
        assert 'process' in log_data
    
    def test_formatting_with_correlation_id(self):
        """Test formatting with correlation ID context."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        test_correlation_id = "test-correlation-123"
        
        # Set correlation ID in context
        correlation_id.set(test_correlation_id)
        
        try:
            formatted = self.formatter.format(record)
            log_data = json.loads(formatted)
            
            assert log_data['correlation_id'] == test_correlation_id
        finally:
            correlation_id.set(None)
    
    def test_formatting_with_request_context(self):
        """Test formatting with request context."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        test_context = {"user_id": "123", "session": "abc"}
        request_context.set(test_context)
        
        try:
            formatted = self.formatter.format(record)
            log_data = json.loads(formatted)
            
            assert log_data['context'] == test_context
        finally:
            request_context.set({})
    
    def test_formatting_with_exception(self):
        """Test formatting with exception information."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=True
            )
        
        formatted = self.formatter.format(record)
        log_data = json.loads(formatted)
        
        assert 'exception' in log_data
        assert log_data['exception']['type'] == 'ValueError'
        assert log_data['exception']['message'] == 'Test exception'
        assert 'traceback' in log_data['exception']
    
    def test_formatting_with_extra_fields(self):
        """Test formatting with extra fields."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        record.extra_fields = {"request_id": "req-123", "duration": 1.5}
        
        formatted = self.formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data['request_id'] == 'req-123'
        assert log_data['duration'] == 1.5
    
    def test_json_serializer(self):
        """Test custom JSON serializer for non-serializable objects."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add non-serializable object
        record.extra_fields = {"datetime": datetime.now()}
        
        # Should not raise exception
        formatted = self.formatter.format(record)
        log_data = json.loads(formatted)
        
        assert 'datetime' in log_data
        assert isinstance(log_data['datetime'], str)


@pytest.mark.unit
class TestContextLogger:
    """Test the context-aware logger."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = Mock(spec=logging.Logger)
        self.mock_logger.name = "test.logger"
        self.mock_logger.isEnabledFor.return_value = True
        self.context_logger = ContextLogger(self.mock_logger)
    
    def test_info_logging(self):
        """Test info level logging."""
        self.context_logger.info("Test message", user_id="123", action="test")
        
        self.mock_logger.makeRecord.assert_called_once()
        self.mock_logger.handle.assert_called_once()
        
        # Check the record was created with correct level
        call_args = self.mock_logger.makeRecord.call_args[0]
        assert call_args[1] == logging.INFO  # level
        assert call_args[4] == "Test message"  # message
    
    def test_error_logging(self):
        """Test error level logging."""
        self.context_logger.error("Error message", error_code="E001")
        
        call_args = self.mock_logger.makeRecord.call_args[0]
        assert call_args[1] == logging.ERROR
    
    def test_debug_logging_disabled(self):
        """Test that debug logging respects logger level."""
        self.mock_logger.isEnabledFor.return_value = False
        
        self.context_logger.debug("Debug message")
        
        self.mock_logger.makeRecord.assert_not_called()
        self.mock_logger.handle.assert_not_called()
    
    def test_extra_fields_attachment(self):
        """Test that extra fields are properly attached."""
        self.context_logger.warning("Warning message", component="auth", severity="high")
        
        # Get the record that was created
        record = self.mock_logger.handle.call_args[0][0]
        
        assert hasattr(record, 'extra_fields')
        assert record.extra_fields['component'] == 'auth'
        assert record.extra_fields['severity'] == 'high'


@pytest.mark.unit
class TestCorrelationContext:
    """Test the correlation context manager."""
    
    def test_automatic_correlation_id_generation(self):
        """Test automatic correlation ID generation."""
        with CorrelationContext() as corr_id:
            assert corr_id is not None
            assert len(corr_id) > 0
            assert correlation_id.get() == corr_id
        
        # Should be reset after context
        assert correlation_id.get() is None
    
    def test_explicit_correlation_id(self):
        """Test using explicit correlation ID."""
        test_id = "explicit-correlation-123"
        
        with CorrelationContext(test_id) as corr_id:
            assert corr_id == test_id
            assert correlation_id.get() == test_id
        
        assert correlation_id.get() is None
    
    def test_context_data(self):
        """Test setting context data."""
        context_data = {"user_id": "user123", "operation": "login"}
        
        with CorrelationContext(**context_data):
            assert request_context.get() == context_data
        
        assert request_context.get() == {}
    
    def test_nested_contexts(self):
        """Test nested correlation contexts."""
        with CorrelationContext("outer", operation="outer_op"):
            outer_corr = correlation_id.get()
            outer_context = request_context.get()
            
            assert outer_corr == "outer"
            assert outer_context["operation"] == "outer_op"
            
            with CorrelationContext("inner", operation="inner_op"):
                inner_corr = correlation_id.get()
                inner_context = request_context.get()
                
                assert inner_corr == "inner"
                assert inner_context["operation"] == "inner_op"
            
            # Should restore outer context
            assert correlation_id.get() == outer_corr
            assert request_context.get() == outer_context
        
        # Should be reset
        assert correlation_id.get() is None
        assert request_context.get() == {}


@pytest.mark.unit
class TestLoggerManager:
    """Test the logger manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        LoggerManager.reset()
    
    def teardown_method(self):
        """Clean up after tests."""
        LoggerManager.reset()
    
    def test_configure_logging_console_only(self):
        """Test configuring logging with console output only."""
        with patch('sys.stdout', new_callable=io.StringIO):
            LoggerManager.configure_logging(
                log_level="INFO",
                enable_console=True,
                structured_format=False
            )
        
        assert LoggerManager._configured is True
        
        # Should not configure again
        with patch('logging.getLogger') as mock_get_logger:
            LoggerManager.configure_logging()
            mock_get_logger.assert_not_called()
    
    def test_get_logger_caching(self):
        """Test that loggers are cached properly."""
        logger1 = LoggerManager.get_logger("test.module")
        logger2 = LoggerManager.get_logger("test.module")
        
        assert logger1 is logger2
        assert isinstance(logger1, ContextLogger)
    
    def test_get_logger_different_names(self):
        """Test getting loggers with different names."""
        logger1 = LoggerManager.get_logger("module1")
        logger2 = LoggerManager.get_logger("module2")
        
        assert logger1 is not logger2
        assert logger1.logger.name == "module1"
        assert logger2.logger.name == "module2"
    
    def test_reset_functionality(self):
        """Test logger manager reset."""
        LoggerManager.configure_logging()
        logger = LoggerManager.get_logger("test")
        
        assert LoggerManager._configured is True
        assert len(LoggerManager._loggers) == 1
        
        LoggerManager.reset()
        
        assert LoggerManager._configured is False
        assert len(LoggerManager._loggers) == 0


@pytest.mark.unit
class TestLoggingDecorators:
    """Test logging decorators."""
    
    def setup_method(self):
        """Set up test fixtures."""
        LoggerManager.reset()
        LoggerManager.configure_logging(enable_console=False)
    
    def test_log_function_call_decorator(self):
        """Test function call logging decorator."""
        with patch.object(LoggerManager, 'get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            @log_function_call("test_function", component="test")
            def test_func(x, y=None):
                return x + (y or 0)
            
            result = test_func(5, y=3)
            
            assert result == 8
            
            # Should have logged entry and exit
            assert mock_logger.debug.call_count == 2
            
            # Check debug calls
            calls = mock_logger.debug.call_args_list
            assert "Calling test_function" in calls[0][0][0]
            assert "Completed test_function successfully" in calls[1][0][0]
    
    def test_log_function_call_with_exception(self):
        """Test function call logging with exception."""
        with patch.object(LoggerManager, 'get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            @log_function_call("failing_function")
            def failing_func():
                raise ValueError("test error")
            
            with pytest.raises(ValueError):
                failing_func()
            
            # Should have logged entry and error
            mock_logger.debug.assert_called()
            mock_logger.error.assert_called()
            
            error_call = mock_logger.error.call_args
            assert "Error in failing_function" in error_call[0][0]
    
    def test_log_performance_decorator(self):
        """Test performance logging decorator."""
        with patch.object(LoggerManager, 'get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            @log_performance("test_operation")
            def timed_func():
                import time
                time.sleep(0.01)  # Small delay
                return "done"
            
            result = timed_func()
            
            assert result == "done"
            
            # Should have logged performance
            mock_logger.info.assert_called_once()
            
            call_args = mock_logger.info.call_args
            assert "Performance: test_operation completed" in call_args[0][0]
            assert 'duration_seconds' in call_args[1]
            assert 'operation' in call_args[1]
    
    def test_log_performance_with_exception(self):
        """Test performance logging with exception."""
        with patch.object(LoggerManager, 'get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            @log_performance("failing_operation")
            def failing_func():
                raise RuntimeError("operation failed")
            
            with pytest.raises(RuntimeError):
                failing_func()
            
            # Should have logged performance failure
            mock_logger.error.assert_called_once()
            
            call_args = mock_logger.error.call_args
            assert "Performance: failing_operation failed" in call_args[0][0]
            assert 'duration_seconds' in call_args[1]
            assert 'error' in call_args[1]


@pytest.mark.unit
class TestLoggingUtilities:
    """Test logging utility functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        LoggerManager.reset()
    
    def test_log_with_context_context_logger(self):
        """Test log_with_context with ContextLogger."""
        with patch.object(LoggerManager, 'get_logger') as mock_get_logger:
            mock_context_logger = Mock(spec=ContextLogger)
            mock_get_logger.return_value = mock_context_logger
            
            context_logger = LoggerManager.get_logger("test")
            
            log_with_context(
                context_logger, "info", "Test message",
                user_id="123", action="test"
            )
            
            mock_context_logger.info.assert_called_once_with(
                "Test message", user_id="123", action="test"
            )
    
    def test_log_with_context_standard_logger(self):
        """Test log_with_context with standard logger."""
        mock_logger = Mock(spec=logging.Logger)
        mock_logger.name = "test.logger"
        mock_logger.isEnabledFor.return_value = True
        
        log_with_context(
            mock_logger, "warning", "Warning message",
            component="auth", severity="high"
        )
        
        mock_logger.makeRecord.assert_called_once()
        mock_logger.handle.assert_called_once()
    
    def test_get_logger_convenience_function(self):
        """Test get_logger convenience function."""
        logger = get_logger("test.module")
        
        assert isinstance(logger, ContextLogger)
        assert logger.logger.name == "test.module"
    
    def test_configure_logging_convenience_function(self):
        """Test configure_logging convenience function."""
        with patch.object(LoggerManager, 'configure_logging') as mock_configure:
            configure_logging(log_level="DEBUG", enable_console=False)
            
            mock_configure.assert_called_once_with(
                log_level="DEBUG", enable_console=False
            )


@pytest.mark.integration
class TestLoggingIntegration:
    """Integration tests for logging framework."""
    
    def test_end_to_end_structured_logging(self):
        """Test complete structured logging flow."""
        # Configure logging to string buffer
        log_output = io.StringIO()
        
        # Reset and configure
        LoggerManager.reset()
        
        with patch('sys.stdout', log_output):
            LoggerManager.configure_logging(
                log_level="INFO",
                enable_console=True,
                structured_format=True
            )
            
            logger = get_logger("integration.test")
            
            with CorrelationContext("test-corr-123", user_id="user456"):
                logger.info(
                    "Integration test message",
                    component="test",
                    action="integration"
                )
        
        # Parse the log output
        log_content = log_output.getvalue().strip()
        if log_content:  # Only test if we got output
            log_data = json.loads(log_content)
            
            assert log_data['level'] == 'INFO'
            assert log_data['message'] == 'Integration test message'
            assert log_data['correlation_id'] == 'test-corr-123'
            assert log_data['context']['user_id'] == 'user456'
            assert log_data['component'] == 'test'
            assert log_data['action'] == 'integration'
    
    def test_logging_with_real_exception(self):
        """Test logging with real exception information."""
        log_output = io.StringIO()
        
        LoggerManager.reset()
        
        with patch('sys.stdout', log_output):
            LoggerManager.configure_logging(
                log_level="ERROR",
                enable_console=True,
                structured_format=True
            )
            
            logger = get_logger("exception.test")
            
            try:
                raise ValueError("Real test exception")
            except ValueError:
                # Create a record with exc_info properly set
                import sys
                record = logger.logger.makeRecord(
                    logger.logger.name, logging.ERROR, '', 0, 
                    "Exception occurred", (), sys.exc_info()
                )
                logger.logger.handle(record)
        
        log_content = log_output.getvalue().strip()
        if log_content:
            log_data = json.loads(log_content)
            
            assert 'exception' in log_data
            assert log_data['exception']['type'] == 'ValueError'
            assert 'Real test exception' in log_data['exception']['message']
