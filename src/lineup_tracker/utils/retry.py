"""
Retry and error handling framework for LineupTracker.

Provides decorators and utilities for handling transient failures,
implementing retry logic, circuit breakers, and graceful degradation.
"""

import asyncio
import time
import random
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional, Union, Any, Dict
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from ..domain.exceptions import LineupMonitorError
from .logging import get_logger

logger = get_logger(__name__)


class BackoffStrategy(Enum):
    """Backoff strategies for retry logic."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter: bool = True
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
    retriable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
    non_retriable_exceptions: Optional[Tuple[Type[Exception], ...]] = None


class RetryExhaustedError(LineupMonitorError):
    """Raised when retry attempts are exhausted."""
    
    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(
            f"Retry exhausted after {attempts} attempts. Last error: {last_exception}"
        )


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"     # Normal operation
    OPEN = "open"         # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: float = 60.0      # Seconds before trying half-open
    success_threshold: int = 3          # Successes to close from half-open
    timeout: float = 30.0               # Operation timeout


class CircuitBreaker:
    """
    Circuit breaker implementation for handling failing services.
    
    Prevents cascading failures by failing fast when a service
    is known to be down.
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_attempt_time: Optional[datetime] = None
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker to a function."""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self._execute_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return self._execute_sync(func, *args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    async def _execute_async(self, func: Callable, *args, **kwargs):
        """Execute async function with circuit breaker logic."""
        if not self._should_attempt():
            raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            # Apply timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure()
            raise
    
    def _execute_sync(self, func: Callable, *args, **kwargs):
        """Execute sync function with circuit breaker logic."""
        if not self._should_attempt():
            raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure()
            raise
    
    def _should_attempt(self) -> bool:
        """Check if we should attempt the operation."""
        now = datetime.now()
        self.last_attempt_time = now
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        elif self.state == CircuitBreakerState.OPEN:
            if (self.last_failure_time and 
                (now - self.last_failure_time).total_seconds() >= self.config.recovery_timeout):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker moving to HALF_OPEN state")
                return True
            return False
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def _record_success(self):
        """Record a successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED - service recovered")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = 0
    
    def _record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker OPENED from HALF_OPEN - service still failing")


class CircuitBreakerOpenError(LineupMonitorError):
    """Raised when circuit breaker is open."""
    pass


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for retry attempt based on strategy."""
    if config.backoff_strategy == BackoffStrategy.FIXED:
        delay = config.base_delay
        
    elif config.backoff_strategy == BackoffStrategy.LINEAR:
        delay = config.base_delay * attempt
        
    elif config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
        delay = config.base_delay * (2 ** (attempt - 1))
        
    elif config.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER:
        delay = config.base_delay * (2 ** (attempt - 1))
        if config.jitter:
            # Add random jitter to prevent thundering herd
            delay *= (0.5 + random.random() * 0.5)
    
    else:
        delay = config.base_delay
    
    # Cap at max delay
    return min(delay, config.max_delay)


def should_retry(exception: Exception, config: RetryConfig) -> bool:
    """Determine if an exception should trigger a retry."""
    # Check non-retriable exceptions first
    if config.non_retriable_exceptions:
        if isinstance(exception, config.non_retriable_exceptions):
            return False
    
    # Check retriable exceptions
    if config.retriable_exceptions:
        return isinstance(exception, config.retriable_exceptions)
    
    # Fall back to general exceptions list
    return isinstance(exception, config.exceptions)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    retriable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    non_retriable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    jitter: bool = True
) -> Callable:
    """
    Retry decorator with configurable backoff strategies.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_strategy: Strategy for calculating delays
        exceptions: Tuple of exceptions that should trigger retry
        retriable_exceptions: Specific exceptions that are retriable
        non_retriable_exceptions: Exceptions that should not be retried
        jitter: Whether to add random jitter to delays
    
    Returns:
        Decorated function with retry logic
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=backoff_strategy,
        exceptions=exceptions,
        retriable_exceptions=retriable_exceptions,
        non_retriable_exceptions=non_retriable_exceptions,
        jitter=jitter
    )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    logger.debug(f"Attempting {func.__name__} (attempt {attempt}/{config.max_attempts})")
                    result = await func(*args, **kwargs)
                    
                    if attempt > 1:
                        logger.info(f"Function {func.__name__} succeeded on attempt {attempt}")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    if not should_retry(e, config):
                        logger.debug(f"Not retrying {func.__name__} due to non-retriable exception: {e}")
                        raise
                    
                    if attempt == config.max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {config.max_attempts} attempts",
                            last_exception=str(e),
                            exception_type=type(e).__name__
                        )
                        raise RetryExhaustedError(config.max_attempts, e)
                    
                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt} of {func.__name__} failed, retrying in {delay:.2f}s: {e}",
                        attempt=attempt,
                        delay=delay,
                        exception_type=type(e).__name__
                    )
                    
                    await asyncio.sleep(delay)
            
            # Should never reach here, but just in case
            raise RetryExhaustedError(config.max_attempts, last_exception)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    logger.debug(f"Attempting {func.__name__} (attempt {attempt}/{config.max_attempts})")
                    result = func(*args, **kwargs)
                    
                    if attempt > 1:
                        logger.info(f"Function {func.__name__} succeeded on attempt {attempt}")
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    if not should_retry(e, config):
                        logger.debug(f"Not retrying {func.__name__} due to non-retriable exception: {e}")
                        raise
                    
                    if attempt == config.max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {config.max_attempts} attempts",
                            last_exception=str(e),
                            exception_type=type(e).__name__
                        )
                        raise RetryExhaustedError(config.max_attempts, e)
                    
                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt} of {func.__name__} failed, retrying in {delay:.2f}s: {e}",
                        attempt=attempt,
                        delay=delay,
                        exception_type=type(e).__name__
                    )
                    
                    time.sleep(delay)
            
            # Should never reach here, but just in case
            raise RetryExhaustedError(config.max_attempts, last_exception)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    success_threshold: int = 3,
    timeout: float = 30.0
) -> Callable:
    """
    Circuit breaker decorator.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying to recover
        success_threshold: Number of successes needed to close circuit
        timeout: Operation timeout in seconds
    
    Returns:
        Decorated function with circuit breaker logic
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        success_threshold=success_threshold,
        timeout=timeout
    )
    
    breaker = CircuitBreaker(config)
    return breaker


def timeout(seconds: float) -> Callable:
    """
    Timeout decorator for async functions.
    
    Args:
        seconds: Timeout in seconds
    
    Returns:
        Decorated function with timeout logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {seconds}s")
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds}s")
        
        return wrapper
    return decorator


def graceful_degradation(fallback_value: Any = None, fallback_func: Optional[Callable] = None):
    """
    Graceful degradation decorator that provides fallback behavior.
    
    Args:
        fallback_value: Value to return on failure
        fallback_func: Function to call for fallback value
    
    Returns:
        Decorated function with graceful degradation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Function {func.__name__} failed, using fallback: {e}",
                    exception_type=type(e).__name__
                )
                
                if fallback_func:
                    try:
                        if asyncio.iscoroutinefunction(fallback_func):
                            return await fallback_func(*args, **kwargs)
                        else:
                            return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback function also failed: {fallback_error}")
                        return fallback_value
                
                return fallback_value
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Function {func.__name__} failed, using fallback: {e}",
                    exception_type=type(e).__name__
                )
                
                if fallback_func:
                    try:
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback function also failed: {fallback_error}")
                        return fallback_value
                
                return fallback_value
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Convenience functions for common retry scenarios
def retry_on_api_error(max_attempts: int = 3):
    """Retry decorator specifically for API errors."""
    from ..domain.exceptions import APIConnectionError, APITimeoutError, APIRateLimitError
    
    return retry(
        max_attempts=max_attempts,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
        retriable_exceptions=(APIConnectionError, APITimeoutError, APIRateLimitError),
        base_delay=2.0,
        max_delay=30.0
    )


def retry_on_network_error(max_attempts: int = 3):
    """Retry decorator for network-related errors."""
    import aiohttp
    
    return retry(
        max_attempts=max_attempts,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
        retriable_exceptions=(
            aiohttp.ClientConnectionError,
            aiohttp.ClientTimeout,
            ConnectionError,
            TimeoutError
        ),
        base_delay=1.0,
        max_delay=15.0
    )


def retry_on_transient_error(max_attempts: int = 2):
    """Retry decorator for transient errors with quick retry."""
    return retry(
        max_attempts=max_attempts,
        backoff_strategy=BackoffStrategy.FIXED,
        base_delay=0.5,
        non_retriable_exceptions=(KeyboardInterrupt, SystemExit)
    )
