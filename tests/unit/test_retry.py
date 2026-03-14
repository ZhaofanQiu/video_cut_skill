"""Tests for retry module."""

from unittest.mock import MagicMock

import pytest

from video_cut_skill.utils.retry import (
    API_RETRY,
    DOWNLOAD_RETRY,
    NETWORK_RETRY,
    RetryableOperation,
    RetryError,
    retry_with_backoff,
)


class TestRetryError:
    """RetryError tests."""

    def test_retry_error_creation(self):
        """Test creating RetryError."""
        error = RetryError("Operation failed")
        assert str(error) == "Operation failed"
        assert error.last_exception is None

    def test_retry_error_with_exception(self):
        """Test RetryError with last exception."""
        original = ValueError("Original error")
        error = RetryError("Operation failed", last_exception=original)
        assert str(error) == "Operation failed"
        assert error.last_exception == original


class TestRetryWithBackoff:
    """retry_with_backoff decorator tests."""

    def test_success_no_retry(self):
        """Test function that succeeds immediately."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_failure(self):
        """Test retry on failure."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Attempt {call_count} failed")
            return "success"

        result = fail_then_succeed()
        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self):
        """Test retry exhaustion."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Attempt {call_count} failed")

        with pytest.raises(RetryError) as exc_info:
            always_fail()

        assert call_count == 3
        assert "failed after 3 attempts" in str(exc_info.value)
        assert isinstance(exc_info.value.last_exception, ValueError)

    def test_specific_exceptions(self):
        """Test retry only on specific exceptions."""
        call_count = 0

        @retry_with_backoff(
            max_attempts=3,
            initial_delay=0.01,
            exceptions=(ConnectionError,),
        )
        def raise_different_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Not retried")  # Won't retry
            raise ConnectionError("Will retry")

        # ValueError is not in exceptions list, so it won't retry
        with pytest.raises(ValueError):
            raise_different_errors()
        assert call_count == 1

    def test_no_jitter(self):
        """Test retry without jitter."""
        call_count = 0

        @retry_with_backoff(max_attempts=2, initial_delay=0.01, jitter=False)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failed")

        with pytest.raises(RetryError):
            always_fail()

    def test_on_retry_callback(self):
        """Test on_retry callback."""
        callback_calls = []

        def on_retry_callback(exc, attempt, delay):
            callback_calls.append((type(exc).__name__, attempt, delay))

        call_count = 0

        @retry_with_backoff(
            max_attempts=3,
            initial_delay=0.01,
            on_retry=on_retry_callback,
        )
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Failed")
            return "success"

        fail_then_succeed()

        assert len(callback_calls) == 2
        assert callback_calls[0][0] == "ValueError"
        assert callback_calls[0][1] == 1
        assert callback_calls[1][1] == 2

    def test_exponential_delay(self):
        """Test exponential delay calculation."""
        delays = []

        def on_retry_callback(exc, attempt, delay):
            delays.append(delay)

        call_count = 0

        @retry_with_backoff(
            max_attempts=4,
            initial_delay=0.1,
            exponential_base=2.0,
            jitter=False,
            on_retry=on_retry_callback,
        )
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failed")

        with pytest.raises(RetryError):
            always_fail()

        # Delays should be approximately: 0.1, 0.2, 0.4
        assert len(delays) == 3
        assert abs(delays[0] - 0.1) < 0.01
        assert abs(delays[1] - 0.2) < 0.01
        assert abs(delays[2] - 0.4) < 0.01

    def test_max_delay_cap(self):
        """Test maximum delay cap."""
        delays = []

        def on_retry_callback(exc, attempt, delay):
            delays.append(delay)

        call_count = 0

        @retry_with_backoff(
            max_attempts=5,
            initial_delay=1.0,
            max_delay=2.0,  # Cap at 2 seconds
            exponential_base=10.0,  # Would normally give huge delays
            jitter=False,
            on_retry=on_retry_callback,
        )
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failed")

        with pytest.raises(RetryError):
            always_fail()

        # All delays should be capped at 2.0
        for delay in delays:
            assert delay <= 2.0

    def test_function_with_args(self):
        """Test retry with function arguments."""
        call_count = 0

        @retry_with_backoff(max_attempts=2, initial_delay=0.01)
        def process_data(data, multiplier=1):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Failed")
            return sum(data) * multiplier

        result = process_data([1, 2, 3], multiplier=2)
        assert result == 12
        assert call_count == 2

    def test_function_with_kwargs(self):
        """Test retry with keyword arguments."""
        call_count = 0

        @retry_with_backoff(max_attempts=2, initial_delay=0.01)
        def process(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Failed")
            return kwargs

        result = process(a=1, b=2)
        assert result == {"a": 1, "b": 2}


class TestRetryableOperation:
    """RetryableOperation class tests."""

    def test_successful_execution(self):
        """Test successful operation execution."""
        operation = MagicMock(return_value="result")

        retry_op = RetryableOperation(operation, max_attempts=3)
        result = retry_op.execute("arg1", key="value")

        assert result == "result"
        assert operation.call_count == 1
        operation.assert_called_once_with("arg1", key="value")

    def test_retry_then_success(self):
        """Test retry then success."""
        call_count = 0

        def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Failed")
            return "success"

        retry_op = RetryableOperation(
            operation,
            max_attempts=5,
            initial_delay=0.01,
            exceptions=(ConnectionError,),
        )

        result = retry_op.execute()
        assert result == "success"
        assert call_count == 3
        assert retry_op.attempt_count == 3

    def test_retry_exhausted(self):
        """Test retry exhausted."""
        operation = MagicMock(side_effect=ValueError("Always fails"))

        retry_op = RetryableOperation(
            operation,
            max_attempts=3,
            initial_delay=0.01,
            exceptions=(ValueError,),
        )

        with pytest.raises(RetryError):
            retry_op.execute()

        assert operation.call_count == 3
        assert retry_op.attempt_count == 3

    def test_specific_exceptions_only(self):
        """Test only specific exceptions trigger retry."""
        operation = MagicMock(side_effect=[ValueError("Not retryable"), "success"])

        retry_op = RetryableOperation(
            operation,
            max_attempts=3,
            initial_delay=0.01,
            exceptions=(ConnectionError,),  # Only retry on ConnectionError
        )

        with pytest.raises(ValueError):
            retry_op.execute()

        # Should not retry on ValueError
        assert operation.call_count == 1


class TestPredefinedRetryConfigs:
    """Predefined retry configuration tests."""

    def test_network_retry(self):
        """Test NETWORK_RETRY configuration."""
        call_count = 0

        @NETWORK_RETRY(initial_delay=0.01)
        def network_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network failed")
            return "success"

        result = network_operation()
        assert result == "success"
        assert call_count == 2

    def test_network_retry_wrong_exception(self):
        """Test NETWORK_RETRY with non-network exception."""
        call_count = 0

        @NETWORK_RETRY(initial_delay=0.01)
        def network_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not a network error")

        with pytest.raises(ValueError):
            network_operation()

        # Should not retry on ValueError
        assert call_count == 1

    def test_download_retry(self):
        """Test DOWNLOAD_RETRY configuration."""
        call_count = 0

        @DOWNLOAD_RETRY(initial_delay=0.01)
        def download_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("Download failed")
            return "success"

        result = download_operation()
        assert result == "success"

    def test_api_retry(self):
        """Test API_RETRY configuration."""
        call_count = 0

        @API_RETRY(initial_delay=0.01)
        def api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("API timeout")
            return "success"

        result = api_call()
        assert result == "success"


class TestRetryEdgeCases:
    """Edge case tests."""

    def test_zero_max_attempts(self):
        """Test with max_attempts effectively minimum behavior."""
        call_count = 0

        @retry_with_backoff(max_attempts=1, initial_delay=0.01)
        def fail_once():
            nonlocal call_count
            call_count += 1
            raise ValueError("Failed")

        with pytest.raises(RetryError):
            fail_once()

        assert call_count == 1

    def test_success_on_last_attempt(self):
        """Test success on the last allowed attempt."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, initial_delay=0.01)
        def succeed_on_last():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Failed")
            return "success"

        result = succeed_on_last()
        assert result == "success"
        assert call_count == 3

    def test_decorator_preserves_function_name(self):
        """Test that decorator preserves function metadata."""

        @retry_with_backoff(max_attempts=2, initial_delay=0.01)
        def my_function():
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."
