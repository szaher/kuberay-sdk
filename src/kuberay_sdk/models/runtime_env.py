"""RuntimeEnv and ExperimentTracking models."""

from __future__ import annotations

import yaml
from pydantic import BaseModel, model_validator

from kuberay_sdk.errors import ValidationError as SDKValidationError


class RuntimeEnv(BaseModel):
    """Ray runtime environment configuration.

    Example:
        >>> env = RuntimeEnv(pip=["torch", "transformers"], env_vars={"KEY": "val"})
        >>> env.to_yaml()
        'pip:\\n- torch\\n- transformers\\nenv_vars:\\n  KEY: val\\n'
    """

    pip: list[str] | None = None
    conda: str | dict | None = None  # type: ignore[type-arg]
    env_vars: dict[str, str] | None = None
    working_dir: str | None = None
    py_modules: list[str] | None = None

    @model_validator(mode="after")
    def _validate_env(self) -> RuntimeEnv:
        if self.pip and self.conda:
            raise SDKValidationError("RuntimeEnv: 'pip' and 'conda' are mutually exclusive (Ray constraint).")
        return self

    def to_dict(self) -> dict:  # type: ignore[type-arg]
        """Convert to a dict suitable for Ray runtime_env."""
        result: dict = {}  # type: ignore[type-arg]
        if self.pip:
            result["pip"] = list(self.pip)
        if self.conda:
            result["conda"] = self.conda
        if self.env_vars:
            result["env_vars"] = dict(self.env_vars)
        if self.working_dir:
            result["working_dir"] = self.working_dir
        if self.py_modules:
            result["py_modules"] = list(self.py_modules)
        return result

    def to_yaml(self) -> str:
        """Serialize to YAML string for runtimeEnvYAML CRD field."""
        return yaml.dump(self.to_dict(), default_flow_style=False)

    def merge_env_vars(self, extra: dict[str, str]) -> RuntimeEnv:
        """Return a new RuntimeEnv with additional env vars merged in."""
        merged = dict(self.env_vars or {})
        merged.update(extra)
        return self.model_copy(update={"env_vars": merged})


class ExperimentTracking(BaseModel):
    """Experiment tracking configuration (MLflow).

    Example:
        >>> et = ExperimentTracking(provider="mlflow", tracking_uri="http://mlflow:5000")
        >>> et.to_env_vars()
        {'MLFLOW_TRACKING_URI': 'http://mlflow:5000'}
    """

    provider: str
    tracking_uri: str
    experiment_name: str | None = None
    env_vars: dict[str, str] | None = None

    @model_validator(mode="after")
    def _validate_provider(self) -> ExperimentTracking:
        if self.provider != "mlflow":
            raise SDKValidationError(f"ExperimentTracking: only 'mlflow' provider is supported, got '{self.provider}'.")
        return self

    def to_env_vars(self) -> dict[str, str]:
        """Generate env vars to inject into RuntimeEnv."""
        result: dict[str, str] = {"MLFLOW_TRACKING_URI": self.tracking_uri}
        if self.experiment_name:
            result["MLFLOW_EXPERIMENT_NAME"] = self.experiment_name
        if self.env_vars:
            result.update(self.env_vars)
        return result
