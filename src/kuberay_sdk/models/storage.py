"""StorageVolume model for PVC management."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, model_validator

from kuberay_sdk.errors import ValidationError as SDKValidationError

_VALID_ACCESS_MODES = {"ReadWriteOnce", "ReadOnlyMany", "ReadWriteMany"}


class StorageVolume(BaseModel):
    """Volume attachment for clusters and jobs.

    Exactly one of ``size`` (new PVC) or ``existing_claim`` (existing PVC) must be set.

    Example:
        >>> # New PVC
        >>> vol = StorageVolume(name="data", size="100Gi", mount_path="/data")
        >>> # Existing PVC
        >>> vol = StorageVolume(name="models", existing_claim="shared-models", mount_path="/models")
    """

    name: str
    mount_path: str
    size: str | None = None
    existing_claim: str | None = None
    access_mode: str = "ReadWriteOnce"
    storage_class: str | None = None

    @model_validator(mode="after")
    def _validate_storage(self) -> StorageVolume:
        if self.size and self.existing_claim:
            raise SDKValidationError("StorageVolume: exactly one of 'size' or 'existing_claim' must be set, not both.")
        if not self.size and not self.existing_claim:
            raise SDKValidationError("StorageVolume: exactly one of 'size' or 'existing_claim' must be set.")
        if not self.mount_path.startswith("/"):
            raise SDKValidationError(f"StorageVolume: mount_path must be an absolute path, got '{self.mount_path}'.")
        if self.access_mode not in _VALID_ACCESS_MODES:
            raise SDKValidationError(
                f"StorageVolume: access_mode must be one of {_VALID_ACCESS_MODES}, got '{self.access_mode}'."
            )
        return self

    def to_volume_spec(self) -> dict[str, Any]:
        """Generate K8s volume spec for the pod template."""
        if self.existing_claim:
            return {
                "name": self.name,
                "persistentVolumeClaim": {"claimName": self.existing_claim},
            }
        return {
            "name": self.name,
            "persistentVolumeClaim": {"claimName": self.name},
        }

    def to_volume_mount(self) -> dict[str, str]:
        """Generate K8s volumeMount entry for a container."""
        return {"name": self.name, "mountPath": self.mount_path}

    def to_pvc_manifest(self, namespace: str) -> dict[str, Any] | None:
        """Generate PVC manifest for new volumes. Returns None for existing claims."""
        if self.existing_claim:
            return None
        pvc: dict[str, Any] = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {"name": self.name, "namespace": namespace},
            "spec": {
                "accessModes": [self.access_mode],
                "resources": {"requests": {"storage": self.size}},
            },
        }
        if self.storage_class:
            pvc["spec"]["storageClassName"] = self.storage_class
        return pvc
