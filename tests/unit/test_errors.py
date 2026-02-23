"""Unit tests for error translation (T074).

Verifies all K8s ApiException status codes map to domain-specific
KubeRayError subclasses with user-friendly messages.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from kuberay_sdk.errors import (
    AuthenticationError,
    ClusterAlreadyExistsError,
    ClusterNotFoundError,
    DashboardUnreachableError,
    JobNotFoundError,
    KubeRayError,
    KubeRayOperatorNotFoundError,
    ResourceConflictError,
    ServiceNotFoundError,
    TimeoutError,
    ValidationError,
    translate_k8s_error,
)


class TestErrorHierarchy:
    """Test error class hierarchy."""

    def test_all_errors_inherit_from_kuberay_error(self) -> None:
        assert issubclass(ClusterNotFoundError, KubeRayError)
        assert issubclass(ClusterAlreadyExistsError, KubeRayError)
        assert issubclass(JobNotFoundError, KubeRayError)
        assert issubclass(ServiceNotFoundError, KubeRayError)
        assert issubclass(DashboardUnreachableError, KubeRayError)
        assert issubclass(KubeRayOperatorNotFoundError, KubeRayError)
        assert issubclass(AuthenticationError, KubeRayError)
        assert issubclass(ValidationError, KubeRayError)
        assert issubclass(ResourceConflictError, KubeRayError)
        assert issubclass(TimeoutError, KubeRayError)

    def test_kuberay_error_has_details(self) -> None:
        err = KubeRayError("test", details={"key": "value"})
        assert err.details == {"key": "value"}

    def test_kuberay_error_default_details(self) -> None:
        err = KubeRayError("test")
        assert err.details == {}


class TestErrorMessages:
    """Test user-friendly error messages (no K8s jargon)."""

    def test_cluster_not_found_message(self) -> None:
        err = ClusterNotFoundError("my-cluster", "default")
        assert "my-cluster" in str(err)
        assert "default" in str(err)
        assert "not found" in str(err)

    def test_job_not_found_message(self) -> None:
        err = JobNotFoundError("my-job", "default")
        assert "my-job" in str(err)
        assert "not found" in str(err)

    def test_service_not_found_message(self) -> None:
        err = ServiceNotFoundError("my-svc", "default")
        assert "my-svc" in str(err)

    def test_dashboard_unreachable_message(self) -> None:
        err = DashboardUnreachableError("my-cluster", "connection refused")
        assert "my-cluster" in str(err)
        assert "not reachable" in str(err)

    def test_operator_not_found_message(self) -> None:
        err = KubeRayOperatorNotFoundError()
        assert "KubeRay operator" in str(err)
        assert "not installed" in str(err)

    def test_authentication_error_message(self) -> None:
        err = AuthenticationError("token expired")
        assert "Authentication failed" in str(err)
        assert "token expired" in str(err)

    def test_timeout_error_message(self) -> None:
        err = TimeoutError("wait_until_ready", 300.0)
        assert "300" in str(err)
        assert "timed out" in str(err)

    def test_resource_conflict_message(self) -> None:
        err = ResourceConflictError("RayCluster", "my-cluster", "default")
        assert "already exists" in str(err)
        assert "different configuration" in str(err)


class TestTranslateK8sError:
    """Test K8s → domain error translation (FR-037)."""

    def _make_api_exc(self, status: int, reason: str = "") -> MagicMock:
        exc = MagicMock()
        exc.status = status
        exc.reason = reason
        return exc

    def test_404_cluster_returns_cluster_not_found(self) -> None:
        exc = self._make_api_exc(404, "Not Found")
        result = translate_k8s_error(exc, resource_kind="RayCluster", resource_name="c1", namespace="ns")
        assert isinstance(result, ClusterNotFoundError)

    def test_404_job_returns_job_not_found(self) -> None:
        exc = self._make_api_exc(404, "Not Found")
        result = translate_k8s_error(exc, resource_kind="RayJob", resource_name="j1", namespace="ns")
        assert isinstance(result, JobNotFoundError)

    def test_404_service_returns_service_not_found(self) -> None:
        exc = self._make_api_exc(404, "Not Found")
        result = translate_k8s_error(exc, resource_kind="RayService", resource_name="s1", namespace="ns")
        assert isinstance(result, ServiceNotFoundError)

    def test_404_unknown_resource(self) -> None:
        exc = self._make_api_exc(404, "Not Found")
        result = translate_k8s_error(exc, resource_kind="Unknown", resource_name="x", namespace="ns")
        assert isinstance(result, KubeRayError)
        assert "not found" in str(result)

    def test_401_returns_authentication_error(self) -> None:
        exc = self._make_api_exc(401, "Unauthorized")
        result = translate_k8s_error(exc)
        assert isinstance(result, AuthenticationError)

    def test_403_returns_authentication_error(self) -> None:
        exc = self._make_api_exc(403, "Forbidden")
        result = translate_k8s_error(exc)
        assert isinstance(result, AuthenticationError)

    def test_409_returns_resource_conflict(self) -> None:
        exc = self._make_api_exc(409, "Conflict")
        result = translate_k8s_error(exc, resource_kind="RayCluster", resource_name="c1", namespace="ns")
        assert isinstance(result, ResourceConflictError)

    def test_422_returns_validation_error(self) -> None:
        exc = self._make_api_exc(422, "Invalid spec")
        result = translate_k8s_error(exc, resource_kind="RayCluster")
        assert isinstance(result, ValidationError)
        assert "Invalid" in str(result)

    def test_500_returns_transient_error(self) -> None:
        exc = self._make_api_exc(500, "Internal Server Error")
        result = translate_k8s_error(exc)
        assert isinstance(result, KubeRayError)
        assert "transient" in str(result).lower()

    def test_503_returns_transient_error(self) -> None:
        exc = self._make_api_exc(503, "Service Unavailable")
        result = translate_k8s_error(exc)
        assert isinstance(result, KubeRayError)

    def test_unknown_status_returns_generic_error(self) -> None:
        exc = self._make_api_exc(418, "I'm a teapot")
        result = translate_k8s_error(exc)
        assert isinstance(result, KubeRayError)

    def test_no_k8s_jargon_in_404_message(self) -> None:
        exc = self._make_api_exc(404, "Not Found")
        result = translate_k8s_error(exc, resource_kind="RayCluster", resource_name="c1", namespace="ns")
        msg = str(result)
        # Should use "Ray cluster" not K8s terms
        assert "Pod" not in msg
        assert "CRD" not in msg
        assert "CustomResource" not in msg

    def test_no_k8s_jargon_in_401_message(self) -> None:
        exc = self._make_api_exc(401, "Unauthorized")
        result = translate_k8s_error(exc)
        msg = str(result)
        assert "kubeconfig" in msg.lower() or "re-authenticate" in msg.lower()
