"""
KubeRay CRD Schema Contracts

This file defines the expected structure of KubeRay CRDs that the SDK
generates. Contract tests verify that SDK-generated resources match
these schemas.

These schemas document the subset of the KubeRay CRD spec that the SDK
uses. Fields not listed here are either not used by the SDK or are
handled via raw_overrides.

API Version: ray.io/v1
Operator compatibility: v1.1+ (tested up to v1.5.1)
"""

# ──────────────────────────────────────────────
# RayCluster CRD Contract
# ──────────────────────────────────────────────

RAYCLUSTER_SCHEMA = {
    "apiVersion": "ray.io/v1",
    "kind": "RayCluster",
    "metadata": {
        "name": str,           # Required: cluster name
        "namespace": str,      # Required: target namespace
        "labels": dict,        # Optional: user labels + Kueue queue label
        "annotations": dict,   # Optional: user annotations
    },
    "spec": {
        "rayVersion": str,     # Informational: e.g., "2.41.0"
        "enableInTreeAutoscaling": bool,  # Optional: default False
        "headGroupSpec": {
            "rayStartParams": {
                "dashboard-host": "0.0.0.0",
                # Additional params from HeadNodeConfig.ray_start_params
            },
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "ray-head",
                            "image": str,  # e.g., "rayproject/ray:2.41.0"
                            "resources": {
                                "requests": {
                                    "cpu": str,     # e.g., "1"
                                    "memory": str,  # e.g., "2Gi"
                                    # "nvidia.com/gpu": str  (if gpus > 0)
                                },
                                "limits": {
                                    "cpu": str,
                                    "memory": str,
                                    # "nvidia.com/gpu": str  (if gpus > 0)
                                },
                            },
                            "volumeMounts": list,  # From StorageVolume configs
                        }
                    ],
                    "volumes": list,           # PVC/volume definitions
                    "nodeSelector": dict,      # Optional: from node_selector or HardwareProfile
                    "tolerations": list,       # Optional: from tolerations or HardwareProfile
                },
            },
        },
        "workerGroupSpecs": [
            {
                "groupName": str,       # Worker group name
                "replicas": int,        # Desired replica count
                "minReplicas": int,     # Min replicas (autoscaling)
                "maxReplicas": int,     # Max replicas (autoscaling)
                "rayStartParams": dict, # Ray start parameters
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "ray-worker",
                                "image": str,
                                "resources": {
                                    "requests": {
                                        "cpu": str,
                                        "memory": str,
                                        # "nvidia.com/gpu": str
                                    },
                                    "limits": {
                                        "cpu": str,
                                        "memory": str,
                                        # "nvidia.com/gpu": str
                                    },
                                },
                                "volumeMounts": list,
                            }
                        ],
                        "volumes": list,
                        "nodeSelector": dict,
                        "tolerations": list,
                    },
                },
            }
        ],
    },
}


# ──────────────────────────────────────────────
# Kueue label contract
# ──────────────────────────────────────────────

KUEUE_QUEUE_LABEL = "kueue.x-k8s.io/queue-name"
KUEUE_PRIORITY_LABEL = "kueue.x-k8s.io/priority-class"

# When queue is set, the label is added to metadata.labels:
# {"kueue.x-k8s.io/queue-name": "<queue-name>"}


# ──────────────────────────────────────────────
# RayJob CRD Contract
# ──────────────────────────────────────────────

RAYJOB_SCHEMA = {
    "apiVersion": "ray.io/v1",
    "kind": "RayJob",
    "metadata": {
        "name": str,
        "namespace": str,
        "labels": dict,
        "annotations": dict,
    },
    "spec": {
        "entrypoint": str,              # Required: e.g., "python train.py"
        "runtimeEnvYAML": str,          # Optional: YAML-serialized runtime_env
        "shutdownAfterJobFinishes": bool,  # Default: True. MUST be True for Kueue.
        "rayClusterSpec": dict,         # Inline cluster spec (same as RayCluster.spec)
        # OR
        # "clusterSelector": dict,      # Select existing cluster (not used with Kueue)
    },
}


# ──────────────────────────────────────────────
# RayService CRD Contract
# ──────────────────────────────────────────────

RAYSERVICE_SCHEMA = {
    "apiVersion": "ray.io/v1",
    "kind": "RayService",
    "metadata": {
        "name": str,
        "namespace": str,
        "labels": dict,
        "annotations": dict,
    },
    "spec": {
        "serveConfigV2": str,   # YAML string with Ray Serve deployment config
        "rayClusterConfig": dict,  # Backing cluster spec
        "serviceUnhealthySecondThreshold": int,    # Optional: default 900
        "deploymentUnhealthySecondThreshold": int,  # Optional: default 300
    },
}


# ──────────────────────────────────────────────
# Dashboard API Contracts
# ──────────────────────────────────────────────

DASHBOARD_JOB_SUBMISSION_PAYLOAD = {
    "entrypoint": str,           # Required: command to run
    "runtime_env": dict,         # Optional: runtime environment
    "entrypoint_num_cpus": int,  # Optional: CPU requirement
    "entrypoint_num_gpus": int,  # Optional: GPU requirement
    "entrypoint_memory": int,    # Optional: memory requirement
    "entrypoint_resources": dict,  # Optional: custom resources
    "metadata": {
        "job_submission_id": str,  # Optional: custom job ID
    },
}

DASHBOARD_JOB_STATUS_RESPONSE = {
    "job_id": str,
    "submission_id": str,
    "status": str,      # PENDING | RUNNING | STOPPED | SUCCEEDED | FAILED
    "entrypoint": str,
    "message": str,     # Error message if failed
    "start_time": int,  # Unix timestamp (ms)
    "end_time": int,    # Unix timestamp (ms), 0 if not completed
    "metadata": dict,
    "runtime_env": dict,
}

# Log streaming endpoint: GET /api/jobs/{job_id}/logs/tail
# Returns: Server-Sent Events (text/event-stream)

# Full logs endpoint: GET /api/jobs/{job_id}/logs
# Returns: {"logs": "<full log string>"}


# ──────────────────────────────────────────────
# OpenShift Route Contract
# ──────────────────────────────────────────────

OPENSHIFT_ROUTE_SCHEMA = {
    "apiVersion": "route.openshift.io/v1",
    "kind": "Route",
    "metadata": {
        "name": str,
        "namespace": str,
    },
    "spec": {
        "host": str,              # Auto-generated if omitted
        "to": {
            "kind": "Service",
            "name": str,          # Target K8s Service name
            "weight": 100,
        },
        "port": {
            "targetPort": int,    # e.g., 8265 for Ray Dashboard
        },
        "tls": {
            "termination": str,   # "edge" (default for SDK-created Routes)
            "insecureEdgeTerminationPolicy": "Redirect",
        },
    },
}


# ──────────────────────────────────────────────
# HardwareProfile Contract (OpenShift AI)
# ──────────────────────────────────────────────

HARDWARE_PROFILE_SCHEMA = {
    "apiVersion": "infrastructure.opendatahub.io/v1",
    "kind": "HardwareProfile",
    "metadata": {
        "name": str,
        "namespace": str,
    },
    "spec": {
        "identifiers": [
            {
                "displayName": str,
                "identifier": str,       # e.g., "cpu", "memory", "nvidia.com/gpu"
                "resourceType": str,     # "CPU" | "Memory" | "Accelerator"
                "defaultCount": str,     # resource.Quantity
                "minCount": str,
                "maxCount": str,
            }
        ],
        "scheduling": {
            "schedulingType": str,       # "Node" | "Queue"
            # When Node:
            "node": {
                "nodeSelector": dict,
                "tolerations": list,
            },
            # When Queue:
            "kueue": {
                "localQueueName": str,
                "priorityClass": str,    # Optional
            },
        },
    },
}
