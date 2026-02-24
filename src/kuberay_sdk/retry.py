"""Retry logic with exponential backoff for transient errors (FR-042, FR-043, FR-044)."""

from __future__ import annotations

import functools
import logging
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

from kuberay_sdk.errors import KubeRayError, TimeoutError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# HTTP status codes considered transient
_TRANSIENT_STATUSES = {500, 502, 503, 504, 429}


def is_transient_error(exc: Exception) -> bool:
    """Check if an exception represents a transient error worth retrying.

    Example:
        >>> from kubernetes.client import ApiException
        >>> is_transient_error(ApiException(status=503))
        True
    """
    status = getattr(exc, "status", None)
    if status and isinstance(status, int) and status in _TRANSIENT_STATUSES:
        return True
    # Network-level errors
    err_str = str(type(exc).__name__).lower()
    return bool(any(term in err_str for term in ("timeout", "connection", "broken")))


def with_retry(
    max_attempts: int = 3,
    backoff_factor: float = 0.5,
    timeout: float = 60.0,
) -> Callable[[F], F]:
    """Decorator for retrying transient errors with exponential backoff.

    Example:
        >>> @with_retry(max_attempts=3, backoff_factor=0.5)
        ... def create_resource():
        ...     api.create_namespaced_custom_object(...)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.monotonic()
            last_exc: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                elapsed = time.monotonic() - start_time
                if elapsed >= timeout:
                    raise TimeoutError(func.__name__, timeout)

                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if not is_transient_error(exc):
                        raise
                    if attempt >= max_attempts:
                        break
                    delay = random.uniform(0, backoff_factor * (2 ** (attempt - 1)))
                    remaining = timeout - (time.monotonic() - start_time)
                    if remaining <= 0:
                        break
                    delay = min(delay, remaining)
                    logger.warning(
                        "Transient error on attempt %d/%d for %s: %s. Retrying in %.1fs...",
                        attempt,
                        max_attempts,
                        func.__name__,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

            if last_exc is not None:
                raise last_exc
            raise KubeRayError(f"Unexpected retry exhaustion in {func.__name__}")

        return wrapper  # type: ignore[return-value]

    return decorator


def idempotent_create(
    create_fn: Callable[..., Any],
    get_fn: Callable[..., Any],
    compare_fn: Callable[[Any, Any], bool],
    desired_spec: Any,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Create a resource idempotently: on conflict, compare specs (FR-043).

    If the resource already exists with an identical spec, return it.
    If different, raise ResourceConflictError.

    Example:
        >>> result = idempotent_create(
        ...     create_fn=api.create_namespaced_custom_object,
        ...     get_fn=api.get_namespaced_custom_object,
        ...     compare_fn=lambda existing, desired: existing["spec"] == desired["spec"],
        ...     desired_spec=cluster_spec,
        ...     group="ray.io", version="v1", namespace="default", plural="rayclusters", body=body,
        ... )
    """
    from kuberay_sdk.errors import ResourceConflictError

    try:
        return create_fn(*args, **kwargs)
    except Exception as exc:
        status = getattr(exc, "status", None)
        if status != 409:
            raise
        # Resource already exists — fetch and compare
        existing = get_fn(*args, **kwargs)
        if compare_fn(existing, desired_spec):
            return existing
        name = desired_spec.get("metadata", {}).get("name", "unknown")
        namespace = desired_spec.get("metadata", {}).get("namespace", "unknown")
        kind = desired_spec.get("kind", "resource")
        raise ResourceConflictError(kind, name, namespace) from exc
