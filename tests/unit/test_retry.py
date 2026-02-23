"""Unit tests for retry logic (T075).

Verifies transient error detection, exponential backoff retry decorator,
and idempotent create behavior with conflict resolution.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kuberay_sdk.errors import ResourceConflictError, TimeoutError
from kuberay_sdk.retry import idempotent_create, is_transient_error, with_retry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_api_exc(status: int) -> Exception:
    """Create a mock exception with a status attribute (like ApiException)."""
    exc = Exception(f"HTTP {status}")
    exc.status = status  # type: ignore[attr-defined]
    return exc


class ConnectionError(Exception):
    """Simulated connection error (name contains 'connection')."""


class TimeoutException(Exception):
    """Simulated timeout error (name contains 'timeout')."""


class BrokenPipeError(Exception):
    """Simulated broken pipe error (name contains 'broken')."""


# ---------------------------------------------------------------------------
# 1. is_transient_error()
# ---------------------------------------------------------------------------


class TestIsTransientError:
    """Test transient error detection."""

    @pytest.mark.parametrize("status", [500, 502, 503, 504, 429])
    def test_transient_status_codes_return_true(self, status: int) -> None:
        exc = _make_api_exc(status)
        assert is_transient_error(exc) is True

    @pytest.mark.parametrize("status", [400, 401, 404, 409, 422])
    def test_non_transient_status_codes_return_false(self, status: int) -> None:
        exc = _make_api_exc(status)
        assert is_transient_error(exc) is False

    def test_timeout_error_type_returns_true(self) -> None:
        exc = TimeoutException("request timed out")
        assert is_transient_error(exc) is True

    def test_connection_error_type_returns_true(self) -> None:
        exc = ConnectionError("connection refused")
        assert is_transient_error(exc) is True

    def test_broken_pipe_error_type_returns_true(self) -> None:
        exc = BrokenPipeError("broken pipe")
        assert is_transient_error(exc) is True

    def test_generic_exception_returns_false(self) -> None:
        exc = ValueError("bad value")
        assert is_transient_error(exc) is False

    def test_generic_runtime_error_returns_false(self) -> None:
        exc = RuntimeError("something went wrong")
        assert is_transient_error(exc) is False

    def test_exception_without_status_attribute_returns_false(self) -> None:
        exc = Exception("plain error")
        assert is_transient_error(exc) is False

    def test_exception_with_non_int_status_returns_false(self) -> None:
        exc = Exception("bad status")
        exc.status = "503"  # type: ignore[attr-defined]
        assert is_transient_error(exc) is False

    def test_exception_with_none_status_returns_false(self) -> None:
        exc = Exception("none status")
        exc.status = None  # type: ignore[attr-defined]
        assert is_transient_error(exc) is False


# ---------------------------------------------------------------------------
# 2. with_retry() decorator
# ---------------------------------------------------------------------------


class TestWithRetry:
    """Test retry decorator with exponential backoff."""

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_succeeds_on_first_attempt_no_retry(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_monotonic.return_value = 0.0

        @with_retry(max_attempts=3)
        def succeed() -> str:
            return "ok"

        result = succeed()
        assert result == "ok"
        mock_sleep.assert_not_called()

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_retries_on_transient_error_then_succeeds(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        # monotonic() called: once at start of each attempt (elapsed check) +
        # once before computing remaining time for delay
        mock_monotonic.return_value = 0.0
        call_count = 0

        @with_retry(max_attempts=3, backoff_factor=1.0, timeout=60.0)
        def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise _make_api_exc(503)
            return "success"

        result = flaky()
        assert result == "success"
        assert call_count == 3
        # Should have slept twice (after attempt 1 and 2)
        assert mock_sleep.call_count == 2

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_does_not_retry_non_transient_error(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_monotonic.return_value = 0.0

        @with_retry(max_attempts=3)
        def fail_hard() -> str:
            raise _make_api_exc(404)

        with pytest.raises(Exception, match="HTTP 404"):
            fail_hard()
        mock_sleep.assert_not_called()

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_does_not_retry_value_error(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_monotonic.return_value = 0.0

        @with_retry(max_attempts=5)
        def bad_input() -> None:
            raise ValueError("invalid input")

        with pytest.raises(ValueError, match="invalid input"):
            bad_input()
        mock_sleep.assert_not_called()

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_exponential_backoff_delays(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_monotonic.return_value = 0.0

        @with_retry(max_attempts=5, backoff_factor=0.5, timeout=60.0)
        def always_fail() -> None:
            raise _make_api_exc(503)

        with pytest.raises(Exception):
            always_fail()

        # Expected delays: 0.5*(2^0)=0.5, 0.5*(2^1)=1.0, 0.5*(2^2)=2.0, 0.5*(2^3)=4.0
        # Sleep called 4 times (after attempts 1, 2, 3, 4; not after attempt 5)
        assert mock_sleep.call_count == 4
        delays = [c.args[0] for c in mock_sleep.call_args_list]
        assert delays == [0.5, 1.0, 2.0, 4.0]

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_raises_timeout_error_when_total_timeout_exceeded(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        # First call to monotonic returns 0 (start_time).
        # Second call (elapsed check on attempt 2) returns past timeout.
        mock_monotonic.side_effect = [0.0, 0.0, 5.0, 11.0]

        @with_retry(max_attempts=5, backoff_factor=1.0, timeout=10.0)
        def slow_fail() -> None:
            raise _make_api_exc(500)

        with pytest.raises(TimeoutError) as exc_info:
            slow_fail()
        assert "timed out" in str(exc_info.value)
        assert "10" in str(exc_info.value)

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_last_exception_raised_after_max_attempts_exhausted(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_monotonic.return_value = 0.0
        attempt = 0

        @with_retry(max_attempts=3, backoff_factor=0.1, timeout=60.0)
        def fail_with_different_messages() -> None:
            nonlocal attempt
            attempt += 1
            exc = Exception(f"failure #{attempt}")
            exc.status = 503  # type: ignore[attr-defined]
            raise exc

        with pytest.raises(Exception, match="failure #3"):
            fail_with_different_messages()
        assert attempt == 3

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_configurable_max_attempts(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_monotonic.return_value = 0.0
        attempts = 0

        @with_retry(max_attempts=5, backoff_factor=0.1, timeout=60.0)
        def count_attempts() -> None:
            nonlocal attempts
            attempts += 1
            raise _make_api_exc(502)

        with pytest.raises(Exception):
            count_attempts()
        assert attempts == 5

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_configurable_backoff_factor(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_monotonic.return_value = 0.0

        @with_retry(max_attempts=3, backoff_factor=2.0, timeout=60.0)
        def always_fail() -> None:
            raise _make_api_exc(429)

        with pytest.raises(Exception):
            always_fail()

        delays = [c.args[0] for c in mock_sleep.call_args_list]
        # 2.0*(2^0)=2.0, 2.0*(2^1)=4.0
        assert delays == [2.0, 4.0]

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_configurable_timeout(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        # timeout=5.0 -- exceed on second attempt
        mock_monotonic.side_effect = [0.0, 6.0]

        @with_retry(max_attempts=10, backoff_factor=0.1, timeout=5.0)
        def slow() -> None:
            raise _make_api_exc(500)

        with pytest.raises(TimeoutError) as exc_info:
            slow()
        assert "5" in str(exc_info.value)

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_delay_capped_by_remaining_timeout(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        # Timeout is 10s. After attempt 1, elapsed is 8s, so remaining=2s.
        # Backoff would be 5.0*(2^0) = 5.0 but should be capped at 2.0.
        mock_monotonic.side_effect = [
            0.0,   # start_time
            0.0,   # elapsed check attempt 1
            8.0,   # remaining check after attempt 1 failure
            8.0,   # elapsed check attempt 2
        ]

        @with_retry(max_attempts=3, backoff_factor=5.0, timeout=10.0)
        def always_fail() -> None:
            raise _make_api_exc(503)

        with pytest.raises(Exception):
            always_fail()

        # First sleep should be capped
        assert mock_sleep.call_count >= 1
        first_delay = mock_sleep.call_args_list[0].args[0]
        assert first_delay == 2.0

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_preserves_function_name_and_docstring(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        @with_retry()
        def my_function() -> None:
            """My docstring."""

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_passes_args_and_kwargs_through(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        mock_monotonic.return_value = 0.0

        @with_retry(max_attempts=1)
        def adder(a: int, b: int, extra: int = 0) -> int:
            return a + b + extra

        assert adder(2, 3, extra=10) == 15

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_timeout_check_before_first_attempt(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """If timeout is already exceeded at the start, raise TimeoutError immediately."""
        # elapsed >= timeout right away
        mock_monotonic.side_effect = [0.0, 100.0]

        @with_retry(max_attempts=3, timeout=1.0)
        def should_not_run() -> str:
            return "should not reach"

        with pytest.raises(TimeoutError):
            should_not_run()

    @patch("kuberay_sdk.retry.time.sleep")
    @patch("kuberay_sdk.retry.time.monotonic")
    def test_breaks_loop_when_remaining_time_zero_after_failure(
        self, mock_monotonic: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """When remaining time is <= 0 after a transient failure, stop immediately."""
        mock_monotonic.side_effect = [
            0.0,   # start_time
            0.0,   # elapsed check attempt 1
            11.0,  # remaining check: 10-11 = -1 <= 0, break
        ]

        @with_retry(max_attempts=5, backoff_factor=0.5, timeout=10.0)
        def always_fail() -> None:
            raise _make_api_exc(500)

        with pytest.raises(Exception, match="HTTP 500"):
            always_fail()
        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# 3. idempotent_create()
# ---------------------------------------------------------------------------


class TestIdempotentCreate:
    """Test idempotent create with conflict resolution (FR-043)."""

    def test_succeeds_on_first_call_no_conflict(self) -> None:
        create_fn = MagicMock(return_value={"metadata": {"name": "cluster-1"}})
        get_fn = MagicMock()
        compare_fn = MagicMock()
        desired_spec = {"kind": "RayCluster", "metadata": {"name": "cluster-1"}}

        result = idempotent_create(
            create_fn, get_fn, compare_fn, desired_spec,
            "group", "v1", namespace="default",
        )

        assert result == {"metadata": {"name": "cluster-1"}}
        create_fn.assert_called_once_with("group", "v1", namespace="default")
        get_fn.assert_not_called()
        compare_fn.assert_not_called()

    def test_returns_existing_on_409_when_specs_match(self) -> None:
        existing_resource = {"metadata": {"name": "cluster-1"}, "spec": {"replicas": 3}}
        conflict_exc = _make_api_exc(409)
        create_fn = MagicMock(side_effect=conflict_exc)
        get_fn = MagicMock(return_value=existing_resource)
        compare_fn = MagicMock(return_value=True)
        desired_spec = {
            "kind": "RayCluster",
            "metadata": {"name": "cluster-1", "namespace": "default"},
            "spec": {"replicas": 3},
        }

        result = idempotent_create(
            create_fn, get_fn, compare_fn, desired_spec,
            "group", "v1", namespace="default",
        )

        assert result == existing_resource
        create_fn.assert_called_once()
        get_fn.assert_called_once_with("group", "v1", namespace="default")
        compare_fn.assert_called_once_with(existing_resource, desired_spec)

    def test_raises_resource_conflict_on_409_when_specs_differ(self) -> None:
        existing_resource = {"metadata": {"name": "cluster-1"}, "spec": {"replicas": 5}}
        conflict_exc = _make_api_exc(409)
        create_fn = MagicMock(side_effect=conflict_exc)
        get_fn = MagicMock(return_value=existing_resource)
        compare_fn = MagicMock(return_value=False)
        desired_spec = {
            "kind": "RayCluster",
            "metadata": {"name": "cluster-1", "namespace": "default"},
            "spec": {"replicas": 3},
        }

        with pytest.raises(ResourceConflictError) as exc_info:
            idempotent_create(
                create_fn, get_fn, compare_fn, desired_spec,
                "group", "v1", namespace="default",
            )

        assert "already exists" in str(exc_info.value)
        assert "different configuration" in str(exc_info.value)
        compare_fn.assert_called_once_with(existing_resource, desired_spec)

    def test_conflict_error_contains_resource_details(self) -> None:
        conflict_exc = _make_api_exc(409)
        create_fn = MagicMock(side_effect=conflict_exc)
        get_fn = MagicMock(return_value={})
        compare_fn = MagicMock(return_value=False)
        desired_spec = {
            "kind": "RayCluster",
            "metadata": {"name": "my-cluster", "namespace": "production"},
        }

        with pytest.raises(ResourceConflictError) as exc_info:
            idempotent_create(create_fn, get_fn, compare_fn, desired_spec)

        err = exc_info.value
        assert err.details["kind"] == "RayCluster"
        assert err.details["name"] == "my-cluster"
        assert err.details["namespace"] == "production"

    def test_conflict_error_defaults_for_missing_metadata(self) -> None:
        conflict_exc = _make_api_exc(409)
        create_fn = MagicMock(side_effect=conflict_exc)
        get_fn = MagicMock(return_value={})
        compare_fn = MagicMock(return_value=False)
        desired_spec = {}  # No kind, metadata

        with pytest.raises(ResourceConflictError) as exc_info:
            idempotent_create(create_fn, get_fn, compare_fn, desired_spec)

        err = exc_info.value
        assert err.details["kind"] == "resource"
        assert err.details["name"] == "unknown"
        assert err.details["namespace"] == "unknown"

    def test_re_raises_non_409_exception(self) -> None:
        create_fn = MagicMock(side_effect=_make_api_exc(500))
        get_fn = MagicMock()
        compare_fn = MagicMock()
        desired_spec = {"kind": "RayCluster", "metadata": {"name": "c1"}}

        with pytest.raises(Exception, match="HTTP 500"):
            idempotent_create(create_fn, get_fn, compare_fn, desired_spec)

        get_fn.assert_not_called()
        compare_fn.assert_not_called()

    def test_re_raises_exception_without_status(self) -> None:
        create_fn = MagicMock(side_effect=RuntimeError("network error"))
        get_fn = MagicMock()
        compare_fn = MagicMock()
        desired_spec = {"kind": "RayCluster", "metadata": {"name": "c1"}}

        with pytest.raises(RuntimeError, match="network error"):
            idempotent_create(create_fn, get_fn, compare_fn, desired_spec)

        get_fn.assert_not_called()

    def test_re_raises_404_exception(self) -> None:
        create_fn = MagicMock(side_effect=_make_api_exc(404))
        get_fn = MagicMock()
        compare_fn = MagicMock()
        desired_spec = {"kind": "RayCluster", "metadata": {"name": "c1"}}

        with pytest.raises(Exception, match="HTTP 404"):
            idempotent_create(create_fn, get_fn, compare_fn, desired_spec)

        get_fn.assert_not_called()

    def test_passes_args_and_kwargs_to_create_and_get(self) -> None:
        existing = {"metadata": {"name": "c1"}}
        conflict_exc = _make_api_exc(409)
        create_fn = MagicMock(side_effect=conflict_exc)
        get_fn = MagicMock(return_value=existing)
        compare_fn = MagicMock(return_value=True)
        desired_spec = {"kind": "RayCluster", "metadata": {"name": "c1"}}

        idempotent_create(
            create_fn, get_fn, compare_fn, desired_spec,
            "ray.io", "v1",
            namespace="default", plural="rayclusters",
        )

        expected_args = ("ray.io", "v1")
        expected_kwargs = {"namespace": "default", "plural": "rayclusters"}
        create_fn.assert_called_once_with(*expected_args, **expected_kwargs)
        get_fn.assert_called_once_with(*expected_args, **expected_kwargs)

    def test_conflict_chains_original_exception(self) -> None:
        """ResourceConflictError should chain the original 409 exception via 'from'."""
        original_exc = _make_api_exc(409)
        create_fn = MagicMock(side_effect=original_exc)
        get_fn = MagicMock(return_value={})
        compare_fn = MagicMock(return_value=False)
        desired_spec = {"kind": "RayCluster", "metadata": {"name": "c1", "namespace": "ns"}}

        with pytest.raises(ResourceConflictError) as exc_info:
            idempotent_create(create_fn, get_fn, compare_fn, desired_spec)

        assert exc_info.value.__cause__ is original_exc
