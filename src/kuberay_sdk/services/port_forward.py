"""PortForwardManager — Dashboard URL discovery with Route/Ingress/port-forward fallback (T031).

Determines the Ray Dashboard URL for a given cluster by:
1. Checking for an OpenShift Route
2. Checking for a Kubernetes Ingress
3. Falling back to kubectl port-forward

Example:
    >>> from kuberay_sdk.services.port_forward import PortForwardManager
    >>> pfm = PortForwardManager(api_client)
    >>> url = pfm.get_dashboard_url("my-cluster", "default")
    >>> print(url)  # e.g., "https://my-cluster-head-svc-default.apps.cluster.example.com"
"""

from __future__ import annotations

import logging
import socket
import subprocess
import time
from typing import Any

from kuberay_sdk.errors import DashboardUnreachableError

logger = logging.getLogger(__name__)

# Ray Dashboard default port
_DASHBOARD_PORT = 8265

# Head service naming convention: <cluster-name>-head-svc
_HEAD_SVC_SUFFIX = "-head-svc"


class PortForwardManager:
    """Manages Ray Dashboard URL discovery and port-forward lifecycle.

    Checks for Route (OpenShift), Ingress (K8s), then falls back to
    kubectl port-forward.

    Example:
        >>> pfm = PortForwardManager(api_client)
        >>> url = pfm.get_dashboard_url("my-cluster", "default")
    """

    def __init__(self, api_client: Any) -> None:
        """Initialize PortForwardManager.

        Args:
            api_client: Kubernetes API client instance.
        """
        self._api_client = api_client
        self._port_forward_process: subprocess.Popen | None = None  # type: ignore[type-arg]

    def get_dashboard_url(self, cluster_name: str, namespace: str) -> str:
        """Get the Ray Dashboard URL for a cluster.

        Tries in order:
        1. OpenShift Route
        2. Kubernetes Ingress
        3. kubectl port-forward (fallback)

        Args:
            cluster_name: Name of the RayCluster.
            namespace: Namespace of the RayCluster.

        Returns:
            The dashboard URL string.

        Raises:
            DashboardUnreachableError: If no method succeeds.

        Example:
            >>> url = pfm.get_dashboard_url("my-cluster", "default")
        """
        # Try OpenShift Route first
        route_url = self._check_route(cluster_name, namespace)
        if route_url:
            logger.info("Found OpenShift Route for cluster '%s': %s", cluster_name, route_url)
            return route_url

        # Try Kubernetes Ingress
        ingress_url = self._check_ingress(cluster_name, namespace)
        if ingress_url:
            logger.info("Found Ingress for cluster '%s': %s", cluster_name, ingress_url)
            return ingress_url

        # Fall back to port-forward
        logger.info(
            "No Route or Ingress found for cluster '%s'. Starting port-forward...",
            cluster_name,
        )
        return self._start_port_forward(cluster_name, namespace)

    def _check_route(self, cluster_name: str, namespace: str) -> str | None:
        """Check for an OpenShift Route for the head service.

        Args:
            cluster_name: Name of the RayCluster.
            namespace: Namespace of the RayCluster.

        Returns:
            Route URL if found, None otherwise.
        """
        head_svc_name = f"{cluster_name}{_HEAD_SVC_SUFFIX}"
        try:
            from kubernetes.client import CustomObjectsApi

            api = CustomObjectsApi(self._api_client)
            # Try to list Routes in the namespace
            routes = api.list_namespaced_custom_object(
                group="route.openshift.io",
                version="v1",
                namespace=namespace,
                plural="routes",
            )
            for route in routes.get("items", []):
                route_spec = route.get("spec", {})
                target = route_spec.get("to", {})
                if target.get("name") == head_svc_name:
                    host = route_spec.get("host", "")
                    if host:
                        # Check if TLS is configured
                        tls = route_spec.get("tls")
                        scheme = "https" if tls else "http"
                        return f"{scheme}://{host}"
        except Exception as exc:
            logger.debug(
                "OpenShift Route check failed (expected on non-OpenShift): %s",
                exc,
            )
        return None

    def _check_ingress(self, cluster_name: str, namespace: str) -> str | None:
        """Check for a Kubernetes Ingress for the head service.

        Args:
            cluster_name: Name of the RayCluster.
            namespace: Namespace of the RayCluster.

        Returns:
            Ingress URL if found, None otherwise.
        """
        head_svc_name = f"{cluster_name}{_HEAD_SVC_SUFFIX}"
        try:
            from kubernetes.client import NetworkingV1Api

            networking_api = NetworkingV1Api(self._api_client)
            ingresses = networking_api.list_namespaced_ingress(namespace=namespace)
            for ingress in ingresses.items:
                if ingress.spec and ingress.spec.rules:
                    for rule in ingress.spec.rules:
                        if rule.http and rule.http.paths:
                            for path in rule.http.paths:
                                backend = path.backend
                                if backend and backend.service and backend.service.name == head_svc_name:
                                    host = rule.host or ""
                                    if host:
                                        # Check TLS
                                        tls_hosts = set()
                                        if ingress.spec.tls:
                                            for tls in ingress.spec.tls:
                                                if tls.hosts:
                                                    tls_hosts.update(tls.hosts)
                                        scheme = "https" if host in tls_hosts else "http"
                                        return f"{scheme}://{host}"
        except Exception as exc:
            logger.debug("Ingress check failed: %s", exc)
        return None

    def _find_free_port(self) -> int:
        """Find a free local port for port-forwarding."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def _start_port_forward(self, cluster_name: str, namespace: str) -> str:
        """Start kubectl port-forward to the head service.

        Args:
            cluster_name: Name of the RayCluster.
            namespace: Namespace of the RayCluster.

        Returns:
            Local URL for the port-forwarded dashboard.

        Raises:
            DashboardUnreachableError: If port-forward fails to start.
        """
        head_svc_name = f"{cluster_name}{_HEAD_SVC_SUFFIX}"
        local_port = self._find_free_port()

        cmd = [
            "kubectl",
            "port-forward",
            f"svc/{head_svc_name}",
            f"{local_port}:{_DASHBOARD_PORT}",
            "-n",
            namespace,
        ]

        try:
            self._port_forward_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait briefly for the port-forward to establish
            time.sleep(2)

            # Check if the process is still running
            if self._port_forward_process.poll() is not None:
                stderr = ""
                if self._port_forward_process.stderr:
                    stderr = self._port_forward_process.stderr.read().decode("utf-8", errors="replace")
                raise DashboardUnreachableError(
                    cluster_name,
                    reason=f"Port-forward process exited immediately. stderr: {stderr}",
                )

            url = f"http://localhost:{local_port}"
            logger.info(
                "Port-forward established: %s -> %s/%s:%d",
                url,
                namespace,
                head_svc_name,
                _DASHBOARD_PORT,
            )
            return url

        except FileNotFoundError as err:
            raise DashboardUnreachableError(
                cluster_name,
                reason="kubectl not found. Please install kubectl to use port-forward fallback.",
            ) from err
        except DashboardUnreachableError:
            raise
        except Exception as exc:
            raise DashboardUnreachableError(
                cluster_name,
                reason=f"Failed to start port-forward: {exc}",
            ) from exc

    def cleanup(self) -> None:
        """Terminate any running port-forward subprocess."""
        if self._port_forward_process is not None:
            try:
                self._port_forward_process.terminate()
                self._port_forward_process.wait(timeout=5)
            except Exception:
                try:
                    self._port_forward_process.kill()
                except Exception:
                    pass
            finally:
                self._port_forward_process = None

    def __del__(self) -> None:
        """Ensure port-forward cleanup on garbage collection."""
        self.cleanup()
