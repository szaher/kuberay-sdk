"""Config file and environment variable support — standalone demo.

Task: T064

The kuberay-sdk resolves configuration from multiple sources with a clear
precedence order:

    explicit SDKConfig args  >  environment variables  >  config file  >  defaults

This script is fully standalone: it creates a *temporary* config file (never
touches ``~/.kuberay/``), sets environment variables in-process, and cleans
everything up at the end.

SECURITY WARNING:
    Never store Kubernetes credentials, tokens, or secrets in the YAML config
    file.  Use kubeconfig, OIDC, or kube-authkit for authentication instead.
    The config file is for non-sensitive SDK tuning (namespace, retry, etc.).
"""

import os
import tempfile
from pathlib import Path

import yaml

from kuberay_sdk.config import SDKConfig, load_config_file, load_env_vars, resolve_config


def main() -> None:
    # ------------------------------------------------------------------
    # Step 1: Show built-in defaults (no config file, no env vars).
    # ------------------------------------------------------------------
    print("=== Step 1: Built-in defaults ===\n")
    defaults = SDKConfig()
    print(f"  namespace:            {defaults.namespace!r}")
    print(f"  retry_max_attempts:   {defaults.retry_max_attempts}")
    print(f"  retry_backoff_factor: {defaults.retry_backoff_factor}")
    print(f"  retry_timeout:        {defaults.retry_timeout}")

    # ------------------------------------------------------------------
    # Step 2: Create a temporary YAML config file.
    # ------------------------------------------------------------------
    print("\n=== Step 2: Config file layer ===\n")

    # Build a sample config dict.
    file_config_data = {
        "namespace": "file-namespace",
        "timeout": 120.0,
        "retry": {
            "max_attempts": 5,
            "backoff_factor": 1.0,
        },
    }

    # Write it to a temp file (automatically cleaned up later).
    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".yaml", prefix="kuberay_config_")
    config_path = Path(tmp_name)
    try:
        with open(tmp_fd, "w") as tmp_file:
            yaml.dump(file_config_data, tmp_file, default_flow_style=False)
        print(f"  Temp config written to: {config_path}")

        # Load and inspect the config file contents.
        loaded = load_config_file(path=config_path)
        print(f"  Loaded from file:       {loaded}")

        # Point the SDK at this temp file via the KUBERAY_CONFIG env var.
        os.environ["KUBERAY_CONFIG"] = str(config_path)

        # ------------------------------------------------------------------
        # Step 3: Add an environment-variable override.
        # ------------------------------------------------------------------
        print("\n=== Step 3: Environment variable layer ===\n")

        # KUBERAY_NAMESPACE overrides whatever the config file says.
        os.environ["KUBERAY_NAMESPACE"] = "env-namespace"
        print("  Set KUBERAY_NAMESPACE=env-namespace")

        env_overrides = load_env_vars()
        print(f"  Env-var overrides: {env_overrides}")

        # ------------------------------------------------------------------
        # Step 4: Resolve with full precedence.
        # ------------------------------------------------------------------
        print("\n=== Step 4: resolve_config() — full precedence ===\n")

        # resolve_config(None) layers:  file values -> env var overrides -> defaults
        resolved = resolve_config()
        print(f"  namespace (env > file > default):   {resolved.namespace!r}")
        print(f"  retry_timeout (file > default):     {resolved.retry_timeout}")
        print(f"  retry_max_attempts (file > default): {resolved.retry_max_attempts}")
        print(f"  retry_backoff_factor (file > default): {resolved.retry_backoff_factor}")

        # ------------------------------------------------------------------
        # Step 5: Explicit SDKConfig wins over everything.
        # ------------------------------------------------------------------
        print("\n=== Step 5: Explicit SDKConfig overrides all ===\n")

        explicit = SDKConfig(namespace="explicit-namespace", retry_timeout=30.0)
        # When an explicit config is passed, resolve_config returns it as-is.
        final = resolve_config(explicit)
        print(f"  namespace (explicit wins): {final.namespace!r}")
        print(f"  retry_timeout (explicit):  {final.retry_timeout}")
        # Fields not set explicitly keep their model defaults.
        print(f"  retry_max_attempts (model default): {final.retry_max_attempts}")

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        print("\n=== Precedence summary ===\n")
        print("  1. Explicit SDKConfig arguments   (highest priority)")
        print("  2. KUBERAY_* environment variables")
        print("  3. ~/.kuberay/config.yaml (or KUBERAY_CONFIG path)")
        print("  4. Built-in defaults              (lowest priority)")
        print("\nDone.")

    finally:
        # ------------------------------------------------------------------
        # Cleanup: remove temp file and unset env vars.
        # ------------------------------------------------------------------
        os.unlink(config_path)
        os.environ.pop("KUBERAY_CONFIG", None)
        os.environ.pop("KUBERAY_NAMESPACE", None)


if __name__ == "__main__":
    main()
