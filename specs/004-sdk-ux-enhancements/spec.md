# Feature Specification: SDK UX & Developer Experience Enhancements

**Feature Branch**: `004-sdk-ux-enhancements`
**Created**: 2026-02-23
**Status**: Draft
**Input**: UX/DX improvement roadmap covering actionable errors, progress feedback, config files, convenience APIs, dry-run mode, presets, compound operations, retry jitter, CLI tool, docs improvements, and capability discovery.

## Clarifications

### Session 2026-02-24

- Q: Should example scripts be runnable standalone (no live cluster) or require a live Kubernetes cluster? → A: Standalone — use dry-run mode or mocks where possible; annotate steps that require a live cluster with comments.
- Q: Should config file documentation warn against storing credentials? → A: Yes — config file is non-sensitive only; auth handled by kubeconfig/kube-authkit. Documentation must include explicit warning.
- Q: Where should the CLI command reference live? → A: Dedicated docs site page (MkDocs); README links to it but does not duplicate the full reference.
- Q: Should documented features include minimum SDK version annotations? → A: Yes — each feature section notes the minimum SDK version required (e.g., "Added in v0.5.0").
- Q: Does a user guide already exist or must US14 create one? → A: New document on docs site — no user guide page exists yet for the 8 new features.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Actionable Error Messages (Priority: P1)

When an SDK operation fails, the user receives an error message that tells them *what* went wrong but not *how to fix it*. Users must search documentation or Stack Overflow for remediation steps. Every SDK error should include a human-readable remediation hint with specific commands or actions to diagnose and resolve the issue.

**Why this priority**: Error recovery is the #1 frustration point. Users who encounter unhelpful errors abandon the SDK. This has the highest impact-to-effort ratio.

**Independent Test**: Trigger each error type (cluster not found, dashboard unreachable, authentication failed, operator missing, timeout) and verify the error message includes a remediation section with actionable steps.

**Acceptance Scenarios**:

1. **Given** a user creates a cluster when the KubeRay operator is not installed, **When** the error is raised, **Then** the error message includes the Helm install command and a link to the installation guide.
2. **Given** a user tries to reach the Ray Dashboard and it is unreachable, **When** the error is raised, **Then** the message includes kubectl commands to check the cluster status, pod logs, and network policies.
3. **Given** a user's authentication fails, **When** the error is raised, **Then** the message suggests checking kubeconfig, re-authenticating, or verifying RBAC permissions.
4. **Given** a user's operation times out, **When** the error is raised, **Then** the message suggests increasing the timeout, checking cluster events, and verifying resource availability.
5. **Given** a user catches any SDK error in code, **When** they access a `remediation` attribute, **Then** they receive a string with step-by-step recovery instructions.

---

### User Story 2 — Progress Feedback for Long Operations (Priority: P2)

When a user calls `wait_until_ready()` or similar blocking operations, the SDK blocks silently for up to 300 seconds with no indication of progress. Users cannot tell if the operation is progressing, stuck, or about to complete. The SDK should provide optional progress feedback via callbacks.

**Why this priority**: Silent blocking is the #2 frustration point, especially in notebooks and interactive sessions. Users kill processes thinking they are frozen.

**Independent Test**: Call `wait_until_ready()` with a progress callback and verify the callback is invoked with status updates at regular intervals.

**Acceptance Scenarios**:

1. **Given** a user calls a blocking wait operation with a progress callback, **When** the operation is in progress, **Then** the callback is invoked at regular intervals with the current status (e.g., state, elapsed time, last event).
2. **Given** a user calls a blocking wait without a callback, **When** the operation is in progress, **Then** the behavior is unchanged from today (silent blocking).
3. **Given** a user calls a blocking wait in a Jupyter notebook, **When** a default progress callback is used, **Then** status updates are printed to stdout in a human-readable format.
4. **Given** a user's wait operation times out, **When** the timeout occurs, **Then** the last known status is included in the timeout error message.

---

### User Story 3 — Configuration File and Environment Variable Support (Priority: P3)

Users who work with a fixed cluster or namespace must pass `SDKConfig(namespace="...")` in every script. The SDK should support loading configuration from a YAML file (`~/.kuberay/config.yaml`) and environment variables (`KUBERAY_NAMESPACE`, `KUBERAY_TIMEOUT`, etc.) to reduce boilerplate.

**Why this priority**: Reduces friction for the most common setup pattern. Low effort with high daily impact for regular users.

**Independent Test**: Set environment variables and/or create a config file, then instantiate `KubeRayClient()` without arguments and verify the configuration is loaded correctly.

**Acceptance Scenarios**:

1. **Given** a user has a `~/.kuberay/config.yaml` file with namespace and timeout settings, **When** they instantiate `KubeRayClient()` without arguments, **Then** the config values from the file are used.
2. **Given** a user sets `KUBERAY_NAMESPACE=my-ns` in the environment, **When** they instantiate `KubeRayClient()`, **Then** the namespace is set to `my-ns`.
3. **Given** both a config file and environment variables exist, **When** there is a conflict, **Then** environment variables take precedence over the config file, and explicit `SDKConfig` arguments take precedence over both.
4. **Given** no config file and no environment variables exist, **When** the user instantiates `KubeRayClient()`, **Then** the behavior is unchanged from today (default values).
5. **Given** a config file contains invalid YAML or unknown fields, **When** the SDK loads it, **Then** a clear validation error is raised explaining the issue and the expected format.

---

### User Story 4 — Better Handle Representations (Priority: P4)

When users inspect handles (ClusterHandle, JobHandle, ServiceHandle) in a REPL, notebook, or debugger, they see unhelpful output like `<ClusterHandle object at 0x...>`. Handles should display a concise, informative summary of the resource state.

**Why this priority**: Improves the notebook/REPL workflow significantly. Data scientists rely on visual inspection. Low effort.

**Independent Test**: Create a handle and call `repr()` on it; verify the output includes the resource name, state, and key metrics.

**Acceptance Scenarios**:

1. **Given** a ClusterHandle for a cluster, **When** the user evaluates the handle in a REPL, **Then** the output shows the cluster name and namespace (e.g., `ClusterHandle(name='my-cluster', namespace='default')`).
2. **Given** a JobHandle for a job, **When** the user evaluates it, **Then** the output includes the job name, namespace, and submission mode (e.g., `JobHandle(name='my-job', namespace='default', mode='DASHBOARD')`).
3. **Given** a ServiceHandle for a service, **When** the user evaluates it, **Then** the output includes the service name and namespace (e.g., `ServiceHandle(name='my-service', namespace='default')`).

---

### User Story 5 — Convenience Re-exports (Priority: P5)

Users must use deep import paths like `from kuberay_sdk.models.cluster import WorkerGroup` to access commonly-used types. Frequently-used models and types should be importable directly from the top-level `kuberay_sdk` package.

**Why this priority**: Reduces import boilerplate. One-time effort that improves every user's first experience.

**Independent Test**: Import commonly-used types from `kuberay_sdk` directly and verify they resolve correctly.

**Acceptance Scenarios**:

1. **Given** a user writes `from kuberay_sdk import WorkerGroup, RuntimeEnv, StorageVolume`, **When** the import executes, **Then** all types are available and functional.
2. **Given** a user uses IDE auto-complete on the `kuberay_sdk` module, **When** they type `kuberay_sdk.`, **Then** commonly-used types appear in suggestions alongside `KubeRayClient` and `SDKConfig`.

---

### User Story 6 — Dry-Run and Validation Mode (Priority: P6)

Users cannot preview the Kubernetes CRD manifest that will be created before calling `create_cluster()`. Misconfigurations are only caught when the Kubernetes API rejects the request. Users should be able to validate configurations and preview manifests without creating resources.

**Why this priority**: Prevents costly mistakes in production. Useful for CI/CD pipelines and review workflows.

**Independent Test**: Call `create_cluster()` with `dry_run=True` and verify it returns the CRD manifest without creating any resource on the cluster.

**Acceptance Scenarios**:

1. **Given** a user calls `create_cluster(..., dry_run=True)`, **When** the call completes, **Then** the full CRD manifest is returned as a dictionary without any resource being created on the cluster.
2. **Given** a user calls `create_cluster()` with invalid parameters and `dry_run=True`, **When** validation runs, **Then** a validation error is raised before any API call is made.
3. **Given** a user wants the manifest as YAML, **When** they call a `to_yaml()` method on the dry-run result, **Then** a valid YAML string is returned that can be applied with `kubectl apply -f`.

---

### User Story 7 — Preset Configurations (Priority: P7)

The `create_cluster()` method has 18 parameters. Users creating common cluster configurations (single GPU node, multi-node data processing, lightweight dev cluster) must specify many parameters manually. The SDK should provide preset configurations for common patterns.

**Why this priority**: Reduces the learning curve for new users. Makes the "happy path" trivially easy.

**Independent Test**: Create a cluster using a preset and verify the resulting configuration matches the expected defaults for that preset.

**Acceptance Scenarios**:

1. **Given** a user creates a cluster with a preset (e.g., `preset="gpu-single"`), **When** the cluster is created, **Then** the configuration uses the preset's default values for worker count, GPU, CPU, and memory.
2. **Given** a user specifies both a preset and explicit parameters, **When** there is a conflict, **Then** explicit parameters override the preset values.
3. **Given** a user lists available presets, **When** they call the listing method, **Then** they receive a list of preset names with descriptions and default values.

---

### User Story 8 — Compound Operations (Priority: P8)

Common workflows like "create cluster, wait until ready, submit job" require 3 separate API calls. The SDK should provide compound methods that chain these operations for the most frequent patterns.

**Why this priority**: Reduces boilerplate for the most common multi-step workflows.

**Independent Test**: Call a compound method and verify it performs all steps in sequence and returns the final result.

**Acceptance Scenarios**:

1. **Given** a user calls a compound "create and submit" method on the client, **When** the operation completes, **Then** the cluster is created, reaches ready state, and the job is submitted — returning a job handle.
2. **Given** a user calls a compound method and the wait step times out, **When** the timeout occurs, **Then** the cluster is left in its current state (not deleted) and a clear error is raised with the cluster's last known status.

---

### User Story 9 — Retry Jitter (Priority: P9)

The SDK's retry mechanism uses exponential backoff without jitter. When multiple SDK clients retry simultaneously (e.g., in a distributed training pipeline), they all retry at the same intervals, causing thundering herd problems on the Kubernetes API server.

**Why this priority**: One-line fix with real production impact for multi-client deployments.

**Independent Test**: Execute multiple retries and verify the delay between attempts is not deterministic — it includes random variance.

**Acceptance Scenarios**:

1. **Given** a retry with exponential backoff is triggered, **When** the delay is calculated, **Then** the delay includes a random jitter component so that two retries with the same parameters produce different delays.
2. **Given** the existing retry behavior, **When** jitter is added, **Then** the maximum possible delay does not exceed 2x the base exponential delay (bounded jitter).

---

### User Story 10 — CLI Tool (Priority: P10)

The SDK has no command-line interface. Users who want to manage Ray resources from the terminal must write Python scripts or use raw kubectl commands. A `kuberay` CLI would make the SDK accessible from shell scripts, CI/CD pipelines, and quick terminal operations.

**Why this priority**: Opens the SDK to non-Python workflows. High effort but high reach.

**Independent Test**: Install the SDK and run `kuberay cluster list` from the terminal; verify it outputs the list of clusters in the current namespace.

**Acceptance Scenarios**:

1. **Given** the SDK is installed, **When** a user runs `kuberay cluster list`, **Then** a table of clusters in the current namespace is displayed with name, state, and worker count.
2. **Given** a user runs `kuberay cluster create my-cluster --workers 4`, **When** the command completes, **Then** a cluster is created and the CLI outputs the cluster name and status.
3. **Given** a user runs `kuberay job create training-run --entrypoint "python train.py" --cluster my-cluster`, **When** the command completes, **Then** a job is submitted and the CLI outputs the job ID and status.
4. **Given** a user runs `kuberay --help`, **When** the help is displayed, **Then** all available commands and options are listed with descriptions.

---

### User Story 11 — Capability Discovery (Priority: P11)

Users cannot programmatically query what features are available on the connected Kubernetes cluster (GPU support, Kueue queue management, OpenShift features). They must try operations and catch errors to discover capabilities. The SDK should provide a method to discover cluster capabilities upfront.

**Why this priority**: Helps users write portable code that adapts to the cluster environment.

**Independent Test**: Call `client.get_capabilities()` and verify it returns a structured object describing available features.

**Acceptance Scenarios**:

1. **Given** a user calls a capabilities discovery method, **When** the cluster has KubeRay, Kueue, and GPU nodes, **Then** the result indicates all three capabilities are available.
2. **Given** a user calls capabilities discovery on a vanilla Kubernetes cluster, **When** only KubeRay is installed, **Then** the result indicates KubeRay is available but Kueue and GPU are not.
3. **Given** a user calls capabilities discovery, **When** the result is inspected, **Then** it includes the KubeRay operator version, available GPU types, and whether OpenShift features are detected.

---

### User Story 12 — Troubleshooting Documentation (Priority: P12)

The SDK documentation has no troubleshooting section. Users encountering common issues (cluster stuck in creating state, dashboard unreachable, authentication failures) must search external resources for solutions. A troubleshooting guide with common failure patterns and solutions should be added to the documentation.

**Why this priority**: Low effort, high impact for reducing support burden.

**Independent Test**: Verify the documentation includes a troubleshooting section with at least 5 common issues and their resolutions.

**Acceptance Scenarios**:

1. **Given** a user reads the troubleshooting documentation, **When** they encounter a common issue, **Then** they find the issue described with symptoms, causes, and step-by-step resolution.
2. **Given** the documentation lists common issues, **When** reviewed, **Then** it covers at minimum: cluster stuck in creating state, dashboard unreachable, authentication failures, operator not found, and job timeout.

---

### User Story 13 — Migration Guide (Priority: P13)

Users familiar with kubectl and raw KubeRay CRDs have no guide for transitioning to the SDK. A "If you know kubectl" migration guide would map kubectl commands to SDK equivalents, accelerating adoption.

**Why this priority**: Low effort documentation that accelerates adoption for the primary target audience.

**Independent Test**: Verify the documentation includes a migration guide mapping at least 10 kubectl commands to SDK equivalents.

**Acceptance Scenarios**:

1. **Given** a user familiar with `kubectl get rayclusters`, **When** they read the migration guide, **Then** they find the SDK equivalent (`client.list_clusters()`) with a side-by-side comparison.
2. **Given** the migration guide, **When** reviewed, **Then** it covers CRUD operations for clusters, jobs, and services with both kubectl and SDK examples.

---

### User Story 14 — Comprehensive Documentation for New Features (Priority: P14)

All 8 new SDK capabilities (dry-run mode, presets, progress callbacks, CLI tool, capability discovery, compound operations, config file/env var support, and convenience re-exports) shipped without corresponding documentation updates to the README, user guide, or example scripts. Users currently have no documentation for these features. The README, user guide, and examples must be updated to cover all 8 features with runnable code snippets.

**Why this priority**: Features without documentation are invisible. Users cannot adopt capabilities they don't know exist. This is the final step to make the UX enhancements usable.

**Independent Test**: Review the README, user guide, and example scripts and verify that every new feature is documented with at least one runnable code snippet per feature.

**Acceptance Scenarios**:

1. **Given** a user reads the README, **When** they look for quick-start examples, **Then** they find usage examples for dry-run mode, presets, CLI tool, config files, and convenience imports.
2. **Given** a user reads the user guide (a new page on the docs site), **When** they look for feature documentation, **Then** each of the 8 new features is covered with usage examples and configuration options.
3. **Given** a user browses the example scripts, **When** they look for demonstrations, **Then** they find example scripts covering dry-run mode, presets, progress callbacks, CLI tool, capability discovery, compound operations, config/env vars, and top-level imports.
4. **Given** a user follows any documented code snippet, **When** they copy and run it, **Then** the snippet is syntactically valid and demonstrates the described feature correctly.

---

### Edge Cases

- What happens when the config file path (`~/.kuberay/config.yaml`) is a directory instead of a file?
- What happens when environment variables contain invalid values (e.g., `KUBERAY_TIMEOUT=abc`)?
- What happens when a progress callback raises an exception during a wait operation?
- What happens when `dry_run=True` is used with the async client?
- What happens when presets are combined with conflicting explicit parameters and `raw_overrides`?
- What happens when capability discovery is called on a cluster where the user lacks RBAC permissions to list CRDs?
- What happens when the CLI is invoked without a valid kubeconfig?
- What happens when a user follows a README example but has an older SDK version that lacks the documented features?

## Requirements *(mandatory)*

### Functional Requirements

**Error Handling (US1)**
- **FR-001**: Every SDK error class MUST include a `remediation` attribute containing human-readable recovery instructions with specific commands or actions.
- **FR-002**: Remediation hints MUST reference relevant kubectl commands, documentation links, or configuration changes appropriate to the error type.
- **FR-003**: The `KubeRayError` base class MUST define the `remediation` attribute so all errors support it consistently.

**Progress Feedback (US2)**
- **FR-004**: Blocking wait methods (e.g., wait until ready, wait for job completion) MUST accept an optional `progress_callback` parameter.
- **FR-005**: When a callback is provided, the SDK MUST invoke it at regular intervals (every 5-10 seconds) with the current resource status and elapsed time.
- **FR-006**: When no callback is provided, blocking wait methods MUST behave identically to the current implementation (silent blocking).
- **FR-007**: When a wait operation times out, the timeout error MUST include the last known resource status.

**Configuration (US3)**
- **FR-008**: The SDK MUST support loading configuration from a YAML file at `~/.kuberay/config.yaml` (or a path specified by `KUBERAY_CONFIG` environment variable).
- **FR-009**: The SDK MUST support loading individual settings from environment variables: `KUBERAY_NAMESPACE`, `KUBERAY_TIMEOUT`, `KUBERAY_RETRY_MAX_ATTEMPTS`, `KUBERAY_RETRY_BACKOFF_FACTOR`.
- **FR-010**: Configuration precedence MUST be: explicit `SDKConfig` arguments > environment variables > config file > built-in defaults.
- **FR-011**: Invalid configuration values (file or env vars) MUST raise a `ValidationError` with a clear message explaining the expected format.

**Handle Representations (US4)**
- **FR-012**: ClusterHandle, JobHandle, and ServiceHandle MUST implement `__repr__` returning a concise summary including the resource name and current state.
- **FR-013**: Handle `__repr__` MUST NOT make API calls; it MUST use cached/known state from the last operation.

**Convenience Imports (US5)**
- **FR-014**: The top-level `kuberay_sdk` package MUST re-export commonly-used types: at minimum `WorkerGroup`, `RuntimeEnv`, `StorageVolume`, `SDKConfig`, `KubeRayClient`, and `AsyncKubeRayClient`.

**Dry-Run Mode (US6)**
- **FR-015**: `create_cluster()`, `create_job()`, and `create_service()` MUST accept a `dry_run` parameter that returns the CRD manifest without creating any resource.
- **FR-016**: Dry-run results MUST include a `to_yaml()` method that returns a valid YAML string.
- **FR-017**: Dry-run mode MUST perform local validation (pydantic model validation) before returning the manifest.

**Presets (US7)**
- **FR-018**: The SDK MUST provide at least 3 built-in presets for common cluster configurations (e.g., dev, GPU, data processing).
- **FR-019**: Users MUST be able to pass a preset name or object to `create_cluster()` to apply preset defaults.
- **FR-020**: Explicit parameters MUST override preset values when both are specified.
- **FR-021**: Users MUST be able to list available presets with their descriptions and default values.

**Compound Operations (US8)**
- **FR-022**: The SDK MUST provide a compound method to create a cluster, wait until ready, and submit a job in a single call.
- **FR-023**: Compound methods MUST NOT delete partially-created resources on failure; they MUST raise an error with the current state.

**Retry Jitter (US9)**
- **FR-024**: The retry mechanism MUST add random jitter to exponential backoff delays.
- **FR-025**: Jitter MUST be bounded so the maximum delay does not exceed 2x the base exponential delay.

**CLI Tool (US10)**
- **FR-026**: The SDK MUST provide a `kuberay` command-line tool installable via pip.
- **FR-027**: The CLI MUST support subcommands for cluster, job, and service operations (create, list, get, delete).
- **FR-028**: The CLI MUST output results in human-readable table format by default, with an option for JSON output.
- **FR-029**: The CLI MUST read configuration from the same sources as the SDK (config file, env vars, flags).

**Capability Discovery (US11)**
- **FR-030**: The SDK MUST provide a method to discover cluster capabilities (KubeRay version, GPU availability, Kueue support, OpenShift detection).
- **FR-031**: Capability discovery MUST gracefully handle permission errors (return "unknown" rather than raising).

**Documentation (US12, US13)**
- **FR-032**: The SDK documentation MUST include a troubleshooting section with at least 5 common issues and resolutions.
- **FR-033**: The SDK documentation MUST include a migration guide mapping kubectl/CRD operations to SDK equivalents.

**Comprehensive Feature Documentation (US14)**
- **FR-034**: The README MUST include sections covering dry-run mode, presets, progress callbacks, CLI tool, capability discovery, compound operations, config file/env var support, and convenience re-exports with usage examples. Each feature section MUST include a version annotation noting the minimum SDK version required (e.g., "Added in v0.5.0").
- **FR-035**: The SDK MUST provide example scripts demonstrating each of the 8 new features with inline comments explaining each step. Examples MUST be runnable standalone (without a live cluster) using dry-run mode or mocks where possible; steps that require a live cluster MUST be annotated with comments.
- **FR-036**: The documentation MUST show the configuration precedence order (explicit args > env vars > config file > defaults) with examples. The config file documentation MUST include an explicit warning that credentials and auth tokens MUST NOT be stored in the config file; authentication is handled by kubeconfig and kube-authkit.
- **FR-037**: The CLI tool documentation MUST include a command reference with all subcommands, options, and output format examples. The command reference MUST be a dedicated page on the docs site (MkDocs); the README MUST link to it but not duplicate the full reference.

### Key Entities

- **Remediation**: A text attribute on error objects containing step-by-step recovery instructions.
- **ProgressStatus**: A data object passed to progress callbacks containing resource state, elapsed time, and last event.
- **ConfigFile**: A YAML file at `~/.kuberay/config.yaml` containing SDK configuration fields.
- **Preset**: A named, reusable cluster configuration with default values for common patterns.
- **ClusterCapabilities**: A structured object returned by capability discovery describing available features.
- **CLI Command**: A terminal command (`kuberay <subcommand>`) that maps to SDK operations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of SDK error types include a non-empty `remediation` attribute with actionable instructions.
- **SC-002**: Users can monitor long-running operations via progress callbacks without modifying the SDK's default behavior.
- **SC-003**: Users can configure the SDK via config file or environment variables, eliminating repeated `SDKConfig` boilerplate across scripts.
- **SC-004**: Handle representations in REPL/notebook environments display the resource name and state in a single line.
- **SC-005**: Commonly-used types are importable from the top-level `kuberay_sdk` package in a single import statement.
- **SC-006**: Users can preview CRD manifests before creating resources, catching misconfigurations before they reach the Kubernetes API.
- **SC-007**: New users can create a correctly-configured cluster using a preset name in a single line of code.
- **SC-008**: The most common multi-step workflow (create cluster + wait + submit job) can be accomplished in a single method call.
- **SC-009**: Retry delays include jitter, eliminating thundering herd behavior in multi-client deployments.
- **SC-010**: Users can manage Ray resources from the terminal without writing Python scripts.
- **SC-011**: Users can programmatically discover cluster capabilities before attempting operations.
- **SC-012**: Common issues are documented with symptoms, causes, and step-by-step resolutions.
- **SC-013**: All 8 new SDK features are documented in the README with at least one runnable code snippet per feature.
- **SC-014**: Example scripts exist for each new feature and pass syntax validation (`ruff check examples/`).

## Assumptions

- The config file format follows standard YAML conventions. The file path `~/.kuberay/config.yaml` follows the XDG convention for user-level configuration. The config file stores only non-sensitive operational settings (namespace, timeout, retry parameters); credentials and auth tokens are handled by kubeconfig and kube-authkit, not the SDK config file.
- Environment variable names use the `KUBERAY_` prefix to avoid conflicts with other tools.
- Presets are opinionated defaults, not exhaustive configuration templates. Users can always override any preset value.
- The CLI tool uses an existing Python CLI framework (not specified here — implementation decision).
- Progress callbacks are synchronous functions. Async callbacks are not required for the initial implementation.
- Capability discovery is best-effort. Missing RBAC permissions result in "unknown" capabilities, not errors.
- The `remediation` attribute on errors is a plain string. Structured remediation (e.g., a list of steps) is deferred to a future iteration.
- Dry-run mode performs local validation only. Server-side dry-run (Kubernetes `--dry-run=server`) is out of scope for the initial implementation.
- The migration guide covers kubectl-to-SDK mapping. Terraform, Helm, or other tool migrations are out of scope.

## Out of Scope

- True native async implementation (replacing ThreadPoolExecutor with native async/await) — significant architectural change deferred to a separate feature.
- Unified job submission abstraction (merging CRD and Dashboard paths) — requires careful API design deferred to a separate feature.
- Cost estimation features — requires external pricing data integration.
- Jupyter magic commands — extension concern, not core SDK.
- Circuit breaker pattern for retries — deferred to a future resilience feature.
