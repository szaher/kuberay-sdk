"""CLI tool usage — invoke the ``kuberay`` command-line interface from Python.

This example demonstrates how to call the ``kuberay`` CLI programmatically
using Python's ``subprocess`` module.  This is useful for:

* Automation scripts that orchestrate cluster lifecycle via shell commands
* Integration testing where you want to verify CLI output
* Wrapping CLI commands in higher-level tooling (e.g., Airflow operators)

The ``kuberay`` CLI is installed as an entry point when the ``kuberay-sdk``
package is installed (``pip install kuberay-sdk``).
"""

from __future__ import annotations

import subprocess


def run_command(cmd: str, description: str) -> None:
    """Run a shell command and print its output.

    Args:
        cmd: The shell command string to execute.
        description: A human-readable label for this command.
    """
    print(f"--- {description} ---")
    print(f"$ {cmd}\n")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # Print stdout if any output was produced.
    if result.stdout:
        print(result.stdout)

    # Print stderr (often contains warnings or error messages).
    if result.stderr:
        print(f"[stderr] {result.stderr}")

    # Report non-zero exit codes.
    if result.returncode != 0:
        print(f"[exit code: {result.returncode}]")

    print()


def main() -> None:
    # ==================================================================
    # Commands that work WITHOUT a running cluster
    # ==================================================================

    # Show the top-level help message and available sub-commands.
    run_command(
        "kuberay --help",
        "Show CLI help",
    )

    # Print the installed kuberay-sdk version.
    run_command(
        "kuberay --version",
        "Show CLI version",
    )

    # ==================================================================
    # Commands that require a Kubernetes cluster with KubeRay installed
    # ==================================================================

    # NOTE: Requires a running KubeRay cluster
    # List all RayClusters in the current namespace (table format).
    run_command(
        "kuberay cluster list",
        "List clusters (table format)",
    )

    # NOTE: Requires a running KubeRay cluster
    # List all RayClusters with JSON output for programmatic parsing.
    run_command(
        "kuberay cluster list --output json",
        "List clusters (JSON format)",
    )

    # NOTE: Requires a running KubeRay cluster
    # Discover cluster capabilities (GPU, Kueue, OpenShift detection).
    run_command(
        "kuberay capabilities",
        "Discover cluster capabilities",
    )

    # NOTE: Requires a running KubeRay cluster
    # Get detailed status of a specific cluster.
    run_command(
        "kuberay cluster status my-cluster",
        "Get cluster status",
    )

    # NOTE: Requires a running KubeRay cluster
    # List jobs submitted to a specific cluster.
    run_command(
        "kuberay job list --cluster my-cluster",
        "List jobs for a cluster",
    )

    # ------------------------------------------------------------------
    # Example: parsing JSON output for automation
    # ------------------------------------------------------------------
    # You can capture JSON output and parse it for downstream logic:
    #
    #   import json
    #
    #   result = subprocess.run(
    #       "kuberay cluster list --output json",
    #       shell=True, capture_output=True, text=True,
    #   )
    #   if result.returncode == 0:
    #       clusters = json.loads(result.stdout)
    #       for cluster in clusters:
    #           print(f"{cluster['name']}: {cluster['state']}")
    # ------------------------------------------------------------------


if __name__ == "__main__":
    main()
