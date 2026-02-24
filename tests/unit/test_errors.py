"""Unit tests for error translation (T074) and remediation (T006-T008).

Verifies all K8s ApiException status codes map to domain-specific
KubeRayError subclasses with user-friendly messages and actionable
remediation hints.
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


class TestRemediationAttribute:
    """Test actionable remediation hints on all error classes (T006)."""

    # ── Base class ──

    def test_kuberay_error_has_remediation_attribute(self) -> None:
        """KubeRayError("msg") has .remediation == "" by default."""
        err = KubeRayError("msg")
        assert hasattr(err, "remediation")
        assert err.remediation == ""

    def test_kuberay_error_custom_remediation(self) -> None:
        """KubeRayError("msg", remediation="fix") stores the hint."""
        err = KubeRayError("msg", remediation="fix")
        assert err.remediation == "fix"

    def test_kuberay_error_details_still_works(self) -> None:
        """Existing KubeRayError(message, details=...) still works (backward compat)."""
        err = KubeRayError("msg", details={"key": "value"})
        assert err.details == {"key": "value"}
        assert err.remediation == ""

    def test_remediation_backward_compatible(self) -> None:
        """Callers using positional message + keyword details must not break."""
        err = KubeRayError("something went wrong", details={"code": 42})
        assert str(err) == "something went wrong"
        assert err.details == {"code": 42}
        assert err.remediation == ""

    def test_kuberay_error_all_three_params(self) -> None:
        """message + remediation + details can all be set together."""
        err = KubeRayError("fail", remediation="try again", details={"a": 1})
        assert str(err) == "fail"
        assert err.remediation == "try again"
        assert err.details == {"a": 1}

    # ── Subclass remediation ──

    def test_cluster_not_found_has_remediation(self) -> None:
        err = ClusterNotFoundError("my-cluster", "default")
        assert err.remediation != ""
        assert "kubectl" in err.remediation.lower()

    def test_cluster_not_found_remediation_includes_namespace(self) -> None:
        err = ClusterNotFoundError("my-cluster", "ml-team")
        assert "ml-team" in err.remediation

    def test_dashboard_unreachable_has_remediation(self) -> None:
        err = DashboardUnreachableError("my-cluster")
        assert err.remediation != ""
        assert "kubectl" in err.remediation.lower()

    def test_operator_not_found_has_remediation(self) -> None:
        err = KubeRayOperatorNotFoundError()
        assert err.remediation != ""
        remediation_lower = err.remediation.lower()
        assert "helm" in remediation_lower or "install" in remediation_lower

    def test_authentication_error_has_remediation(self) -> None:
        err = AuthenticationError()
        assert err.remediation != ""
        assert "kubeconfig" in err.remediation.lower()

    def test_timeout_error_has_remediation(self) -> None:
        err = TimeoutError("wait_until_ready", 60.0)
        assert err.remediation != ""
        remediation_lower = err.remediation.lower()
        assert "timeout" in remediation_lower or "events" in remediation_lower

    def test_cluster_already_exists_has_remediation(self) -> None:
        err = ClusterAlreadyExistsError("c1", "default")
        assert err.remediation != ""

    def test_job_not_found_has_remediation(self) -> None:
        err = JobNotFoundError("j1", "default")
        assert err.remediation != ""
        assert "kubectl" in err.remediation.lower()

    def test_service_not_found_has_remediation(self) -> None:
        err = ServiceNotFoundError("s1", "default")
        assert err.remediation != ""
        assert "kubectl" in err.remediation.lower()

    def test_validation_error_has_remediation_when_provided(self) -> None:
        err = ValidationError("bad input", remediation="check your spec")
        assert err.remediation == "check your spec"

    def test_resource_conflict_has_remediation(self) -> None:
        err = ResourceConflictError("RayCluster", "c1", "default")
        assert err.remediation != ""

    def test_all_error_subclasses_have_remediation(self) -> None:
        """Every concrete error subclass that takes constructor args
        must produce a non-empty remediation string."""
        errors = [
            ClusterNotFoundError("c1", "ns"),
            ClusterAlreadyExistsError("c1", "ns"),
            JobNotFoundError("j1", "ns"),
            ServiceNotFoundError("s1", "ns"),
            DashboardUnreachableError("c1"),
            KubeRayOperatorNotFoundError(),
            AuthenticationError(),
            ResourceConflictError("RayCluster", "c1", "ns"),
            TimeoutError("op", 30.0),
        ]
        for err in errors:
            assert err.remediation != "", (
                f"{type(err).__name__} must have a non-empty remediation"
            )


class TestTranslateK8sErrorRemediation:
    """Test that translate_k8s_error() populates remediation hints (T008)."""

    def _make_api_exc(self, status: int, reason: str = "") -> MagicMock:
        exc = MagicMock()
        exc.status = status
        exc.reason = reason
        return exc

    def test_404_cluster_has_remediation(self) -> None:
        exc = self._make_api_exc(404, "Not Found")
        result = translate_k8s_error(
            exc, resource_kind="RayCluster", resource_name="c1", namespace="ns"
        )
        assert result.remediation != ""
        assert "kubectl" in result.remediation.lower()

    def test_404_job_has_remediation(self) -> None:
        exc = self._make_api_exc(404, "Not Found")
        result = translate_k8s_error(
            exc, resource_kind="RayJob", resource_name="j1", namespace="ns"
        )
        assert result.remediation != ""

    def test_404_service_has_remediation(self) -> None:
        exc = self._make_api_exc(404, "Not Found")
        result = translate_k8s_error(
            exc, resource_kind="RayService", resource_name="s1", namespace="ns"
        )
        assert result.remediation != ""

    def test_404_unknown_has_remediation(self) -> None:
        exc = self._make_api_exc(404, "Not Found")
        result = translate_k8s_error(
            exc, resource_kind="Unknown", resource_name="x", namespace="ns"
        )
        assert result.remediation != ""

    def test_401_has_remediation(self) -> None:
        exc = self._make_api_exc(401, "Unauthorized")
        result = translate_k8s_error(exc)
        assert result.remediation != ""
        assert "kubeconfig" in result.remediation.lower()

    def test_403_has_remediation(self) -> None:
        exc = self._make_api_exc(403, "Forbidden")
        result = translate_k8s_error(exc)
        assert result.remediation != ""

    def test_409_has_remediation(self) -> None:
        exc = self._make_api_exc(409, "Conflict")
        result = translate_k8s_error(
            exc, resource_kind="RayCluster", resource_name="c1", namespace="ns"
        )
        assert result.remediation != ""

    def test_422_has_remediation(self) -> None:
        exc = self._make_api_exc(422, "Invalid spec")
        result = translate_k8s_error(exc, resource_kind="RayCluster")
        assert result.remediation != ""

    def test_500_has_remediation(self) -> None:
        exc = self._make_api_exc(500, "Internal Server Error")
        result = translate_k8s_error(exc)
        assert result.remediation != ""

    def test_503_has_remediation(self) -> None:
        exc = self._make_api_exc(503, "Service Unavailable")
        result = translate_k8s_error(exc)
        assert result.remediation != ""
