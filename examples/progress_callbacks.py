"""Progress callbacks — monitor long-running operations with real-time status updates.

This example demonstrates how to use progress callbacks to observe the
lifecycle of a RayCluster as it transitions through provisioning states.

Key concepts:
1. Define a callback function matching the ``Callable[[ProgressStatus], None]`` signature
2. Pass the callback to ``cluster.wait_until_ready(progress_callback=...)``
3. The SDK invokes the callback each time the cluster's state changes or a
   heartbeat interval elapses, giving you access to elapsed time, state
   description, and optional metadata

Advanced integration with tqdm (progress bars) is shown in a comment block
at the end of this script.
"""

from __future__ import annotations

from collections.abc import Callable

from kuberay_sdk import KubeRayClient
from kuberay_sdk.errors import TimeoutError
from kuberay_sdk.models.progress import ProgressStatus


def on_progress(status: ProgressStatus) -> None:
    """Print a human-readable line each time the SDK reports progress.

    Args:
        status: A ProgressStatus object with the following fields:
            - state (str): Current lifecycle state, e.g. "Pending", "Running".
            - elapsed_seconds (float): Wall-clock seconds since the wait began.
            - message (str): Human-readable description of what is happening.
            - metadata (dict): Optional provider-specific details.
    """
    # Format elapsed time as MM:SS for readability.
    minutes, seconds = divmod(int(status.elapsed_seconds), 60)
    elapsed = f"{minutes:02d}:{seconds:02d}"

    print(f"[{elapsed}] {status.state}: {status.message}")

    # Metadata may contain extra details such as pod counts or conditions.
    if status.metadata:
        for key, value in status.metadata.items():
            print(f"         {key}: {value}")


def main() -> None:
    # Create a client using the default kubeconfig context and namespace.
    client = KubeRayClient()

    # --- Demonstrate the callback type signature ---
    # The expected signature for any progress callback:
    #   progress_callback: Callable[[ProgressStatus], None]
    # You can use a plain function (as above), a lambda, or a bound method.
    callback: Callable[[ProgressStatus], None] = on_progress

    # NOTE: Requires a running KubeRay cluster
    # Create a small cluster and wait for it with progress reporting.
    print("Creating cluster with progress monitoring...\n")
    cluster = client.create_cluster("progress-demo", workers=2)

    try:
        # NOTE: Requires a running KubeRay cluster
        # The callback fires on every state transition and at regular heartbeat
        # intervals while the cluster is not yet ready.
        cluster.wait_until_ready(
            timeout=300,
            progress_callback=callback,
        )
        print("\nCluster is ready!")
    except TimeoutError:
        print("\nCluster did not become ready within the timeout period.")
    finally:
        # NOTE: Requires a running KubeRay cluster
        # Clean up regardless of outcome.
        cluster.delete()
        print("Cluster deleted.")

    # ----------------------------------------------------------------
    # Advanced: tqdm progress-bar integration
    # ----------------------------------------------------------------
    # If you have tqdm installed, you can wrap the callback to drive a
    # progress bar instead of printing lines:
    #
    #   from tqdm import tqdm
    #
    #   bar = tqdm(total=100, desc="Cluster startup", unit="%")
    #
    #   def tqdm_callback(status: ProgressStatus) -> None:
    #       # Map known states to approximate progress percentages.
    #       state_pct = {
    #           "Pending": 10,
    #           "Creating": 30,
    #           "Scheduling": 50,
    #           "Starting": 70,
    #           "Running": 100,
    #       }
    #       pct = state_pct.get(status.state, bar.n)
    #       bar.update(pct - bar.n)
    #       bar.set_postfix_str(status.message)
    #
    #   cluster.wait_until_ready(progress_callback=tqdm_callback)
    #   bar.close()
    # ----------------------------------------------------------------


if __name__ == "__main__":
    main()
