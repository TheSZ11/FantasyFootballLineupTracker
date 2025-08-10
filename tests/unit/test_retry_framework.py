"""
Unit tests for retry and error handling framework.

Tests the retry decorators, circuit breakers, and error handling
utilities to ensure reliability in the face of transient failures.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from src.lineup_tracker.utils.retry import (
    retry, circuit_breaker, timeout, graceful_degradation,
    RetryConfig, BackoffStrategy, calculate_delay, should_retry,
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState,
    RetryExhaustedError, CircuitBreakerOpenError,
    retry_on_api_error, retry_on_network_error
)
from src.lineup_tracker.domain.exceptions import APIConnectionError, APITimeoutError


@pytest.mark.unit
class TestRetryFramework:
    """Test the retry framework components."""
    
    def test_calculate_delay_fixed(self):
        """Test fixed backoff strategy."""
        config = RetryConfig(
            base_delay=2.0,
            backoff_strategy=BackoffStrategy.FIXED
        )
        
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(3, config) == 2.0
        assert calculate_delay(5, config) == 2.0
    
    def test_calculate_delay_linear(self):
        """Test linear backoff strategy."""
        config = RetryConfig(
            base_delay=1.0,
            backoff_strategy=BackoffStrategy.LINEAR
        )
        
        assert calculate_delay(1, config) == 1.0
        assert calculate_delay(2, config) == 2.0
        assert calculate_delay(3, config) == 3.0
    
    def test_calculate_delay_exponential(self):
        """Test exponential backoff strategy."""
        config = RetryConfig(
            base_delay=1.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL
        )
        
        assert calculate_delay(1, config) == 1.0
        assert calculate_delay(2, config) == 2.0
        assert calculate_delay(3, config) == 4.0
        assert calculate_delay(4, config) == 8.0
    
    def test_calculate_delay_max_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=5.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL
        )
        
        assert calculate_delay(10, config) == 5.0  # Would be 512 without cap
    
    def test_should_retry_with_retriable_exceptions(self):
        """Test retry decision with specific retriable exceptions."""
        config = RetryConfig(
            retriable_exceptions=(ValueError, TypeError)
        )
        
        assert should_retry(ValueError("test"), config) is True
        assert should_retry(TypeError("test"), config) is True
        assert should_retry(RuntimeError("test"), config) is False
    
    def test_should_retry_with_non_retriable_exceptions(self):
        """Test retry decision with non-retriable exceptions."""
        config = RetryConfig(
            non_retriable_exceptions=(KeyboardInterrupt, SystemExit),
            exceptions=(Exception,)
        )
        
        assert should_retry(ValueError("test"), config) is True
        assert should_retry(KeyboardInterrupt(), config) is False
        assert should_retry(SystemExit(), config) is False
    
    @pytest.mark.asyncio
    async def test_retry_decorator_success_first_attempt(self):
        """Test retry decorator when function succeeds on first attempt."""
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_func()
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_decorator_success_after_failures(self):
        """Test retry decorator when function succeeds after some failures."""
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary failure")
            return "success"
        
        result = await test_func()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_decorator_exhausted(self):
        """Test retry decorator when all attempts fail."""
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent failure")
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            await test_func()
        
        assert exc_info.value.attempts == 3
        assert "persistent failure" in str(exc_info.value.last_exception)
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_decorator_non_retriable_exception(self):
        """Test retry decorator with non-retriable exception."""
        call_count = 0
        
        @retry(
            max_attempts=3,
            base_delay=0.01,
            non_retriable_exceptions=(KeyboardInterrupt,)
        )
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise KeyboardInterrupt("stop")
        
        with pytest.raises(KeyboardInterrupt):
            await test_func()
        
        assert call_count == 1  # Should not retry
    
    def test_retry_decorator_sync_function(self):
        """Test retry decorator with synchronous function."""
        call_count = 0
        
        @retry(max_attempts=3, base_delay=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("failure")
            return "success"
        
        result = test_func()
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_timeout_decorator(self):
        """Test timeout decorator."""
        @timeout(0.1)
        async def slow_func():
            await asyncio.sleep(0.2)
            return "too slow"
        
        with pytest.raises(TimeoutError):
            await slow_func()
    
    @pytest.mark.asyncio
    async def test_timeout_decorator_success(self):
        """Test timeout decorator with function that completes in time."""
        @timeout(0.2)
        async def fast_func():
            await asyncio.sleep(0.05)
            return "fast enough"
        
        result = await fast_func()
        assert result == "fast enough"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_with_value(self):
        """Test graceful degradation with fallback value."""
        @graceful_degradation(fallback_value="fallback")
        async def failing_func():
            raise ValueError("failure")
        
        result = await failing_func()
        assert result == "fallback"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_with_function(self):
        """Test graceful degradation with fallback function."""
        async def fallback_func():
            return "fallback_result"
        
        @graceful_degradation(fallback_func=fallback_func)
        async def failing_func():
            raise ValueError("failure")
        
        result = await failing_func()
        assert result == "fallback_result"
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_success(self):
        """Test graceful degradation when function succeeds."""
        @graceful_degradation(fallback_value="fallback")
        async def working_func():
            return "success"
        
        result = await working_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_retry_on_api_error(self):
        """Test API-specific retry decorator."""
        call_count = 0
        
        @retry_on_api_error(max_attempts=3)
        async def api_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIConnectionError("API down")
            return "api_result"
        
        result = await api_func()
        
        assert result == "api_result"
        assert call_count == 2


@pytest.mark.unit
class TestCircuitBreaker:
    """Test the circuit breaker implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            success_threshold=2,
            timeout=0.5
        )
        self.breaker = CircuitBreaker(self.config)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_normal_operation(self):
        """Test circuit breaker in normal operation (closed state)."""
        call_count = 0
        
        @self.breaker
        async def test_func():
            nonlocal call_count
            call_count += 1
            return f"call_{call_count}"
        
        # Should work normally
        result1 = await test_func()
        result2 = await test_func()
        
        assert result1 == "call_1"
        assert result2 == "call_2"
        assert self.breaker.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test that circuit breaker opens after threshold failures."""
        call_count = 0
        
        @self.breaker
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"failure_{call_count}")
        
        # First 3 failures should be attempted
        for i in range(3):
            with pytest.raises(ValueError):
                await failing_func()
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        assert call_count == 3
        
        # Next call should fail immediately without calling function
        with pytest.raises(CircuitBreakerOpenError):
            await failing_func()
        
        assert call_count == 3  # Function not called
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery through half-open state."""
        call_count = 0
        
        @self.breaker
        async def recovering_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ValueError(f"failure_{call_count}")
            return f"success_{call_count}"
        
        # Trip the circuit breaker
        for i in range(3):
            with pytest.raises(ValueError):
                await recovering_func()
        
        assert self.breaker.state == CircuitBreakerState.OPEN
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Next call should move to half-open
        result = await recovering_func()
        assert result == "success_4"
        assert self.breaker.state == CircuitBreakerState.HALF_OPEN
        
        # Another success should close the circuit
        result = await recovering_func()
        assert result == "success_5"
        assert self.breaker.state == CircuitBreakerState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_failure(self):
        """Test circuit breaker opening again from half-open on failure."""
        # Manually set to half-open state
        self.breaker.state = CircuitBreakerState.HALF_OPEN
        self.breaker.last_failure_time = datetime.now() - timedelta(seconds=2)
        
        @self.breaker
        async def still_failing_func():
            raise ValueError("still failing")
        
        # Failure in half-open should immediately go back to open
        with pytest.raises(ValueError):
            await still_failing_func()
        
        assert self.breaker.state == CircuitBreakerState.OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_timeout(self):
        """Test circuit breaker timeout functionality."""
        @self.breaker
        async def slow_func():
            await asyncio.sleep(1.0)  # Longer than timeout
            return "too slow"
        
        with pytest.raises(asyncio.TimeoutError):
            await slow_func()
        
        # Should count as a failure
        assert self.breaker.failure_count == 1
    
    def test_circuit_breaker_sync_function(self):
        """Test circuit breaker with synchronous function."""
        call_count = 0
        
        # Create a new breaker for sync test to avoid timeout issues
        sync_config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=1,
            timeout=1.0
        )
        sync_breaker = CircuitBreaker(sync_config)
        
        @sync_breaker
        def sync_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ValueError("sync failure")
            return "sync success"
        
        # Trip the breaker
        for i in range(2):
            with pytest.raises(ValueError):
                sync_func()
        
        assert sync_breaker.state == CircuitBreakerState.OPEN
        
        # Should fail fast
        with pytest.raises(CircuitBreakerOpenError):
            sync_func()
        
        assert call_count == 2
    
    def test_circuit_breaker_decorator_factory(self):
        """Test circuit breaker decorator factory."""
        @circuit_breaker(failure_threshold=2, recovery_timeout=0.1)
        def test_func():
            raise ValueError("test failure")
        
        # Should work as decorator
        with pytest.raises(ValueError):
            test_func()
    
    def test_circuit_breaker_state_transitions(self):
        """Test circuit breaker state transition logic."""
        # Start closed
        assert self.breaker.state == CircuitBreakerState.CLOSED
        
        # Record failures
        for i in range(2):
            self.breaker._record_failure()
            assert self.breaker.state == CircuitBreakerState.CLOSED
        
        # Third failure should open
        self.breaker._record_failure()
        assert self.breaker.state == CircuitBreakerState.OPEN
        
        # Success in closed state should reset failure count
        self.breaker.state = CircuitBreakerState.CLOSED
        self.breaker._record_success()
        assert self.breaker.failure_count == 0


@pytest.mark.integration
class TestRetryIntegration:
    """Integration tests for retry framework."""
    
    @pytest.mark.asyncio
    async def test_retry_with_circuit_breaker(self):
        """Test retry decorator combined with circuit breaker."""
        call_count = 0
        
        @circuit_breaker(failure_threshold=2, recovery_timeout=0.1)
        @retry(max_attempts=3, base_delay=0.01)
        async def combined_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("always fails")
        
        # Retry decorator runs first, so it should exhaust retries
        with pytest.raises(RetryExhaustedError):
            await combined_func()
        
        # Circuit breaker should prevent further attempts
        with pytest.raises(CircuitBreakerOpenError):
            await combined_func()
    
    @pytest.mark.asyncio
    async def test_timeout_with_retry(self):
        """Test timeout decorator combined with retry."""
        call_count = 0
        
        @retry(max_attempts=2, base_delay=0.01)
        @timeout(0.1)
        async def timeout_retry_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.2)  # Will timeout
            return "never reached"
        
        # Should retry timeouts
        with pytest.raises(RetryExhaustedError):
            await timeout_retry_func()
        
        assert call_count == 2  # Should have retried once
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_with_retry(self):
        """Test graceful degradation combined with retry."""
        call_count = 0
        
        @graceful_degradation(fallback_value="degraded")
        @retry(max_attempts=2, base_delay=0.01)
        async def degraded_retry_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent failure")
        
        result = await degraded_retry_func()
        
        assert result == "degraded"
        assert call_count == 2  # Should have attempted retry
