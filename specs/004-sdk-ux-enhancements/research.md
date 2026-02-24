# Research: SDK UX & Developer Experience Enhancements

**Feature**: 004-sdk-ux-enhancements
**Date**: 2026-02-23

## R1: CLI Framework Selection

**Decision**: `click` (v8.x)

**Rationale**: Click is the standard for Python CLI tools with subcommand structure. It provides:
- Declarative command/group structure matching `kuberay cluster|job|service` hierarchy
- Auto-generated `--help` for all commands
- Type-checked parameters with validation
- Shell completion support (bash, zsh, fish)
- Extensive testing utilities (`CliRunner`)
- Minimal transitive dependencies (only `colorama` on Windows)

**Alternatives considered**:
- `argparse` (stdlib): Rejected — excessive boilerplate for nested subcommands, no auto-completion, poor testing story.
- `typer`: Rejected — adds `click` as a dependency anyway, plus `rich` and `typing-extensions`. Type-hint-based API is elegant but less explicit for complex subcommand trees.
- `fire`: Rejected — introspection-based approach is too magical for a public SDK CLI. Limited control over help text and parameter validation.

## R2: Config File Format and Loading Strategy

**Decision**: YAML config file at `~/.kuberay/config.yaml` with `KUBERAY_*` environment variable overrides.

**Rationale**: YAML is already a project dependency (PyYAML) and aligns with the Kubernetes ecosystem convention. The config file path follows the `~/.toolname/` pattern used by kubectl, helm, and other K8s tools.

**Loading precedence**: `SDKConfig(explicit args)` > `KUBERAY_*` env vars > `~/.kuberay/config.yaml` > built-in defaults.

**Config file schema**:
```yaml
namespace: my-namespace
timeout: 120
retry:
  max_attempts: 5
  backoff_factor: 1.0
```

**Environment variables**:
- `KUBERAY_CONFIG` — override config file path
- `KUBERAY_NAMESPACE` — default namespace
- `KUBERAY_TIMEOUT` — default timeout (seconds)
- `KUBERAY_RETRY_MAX_ATTEMPTS` — retry count
- `KUBERAY_RETRY_BACKOFF_FACTOR` — backoff multiplier

**Alternatives considered**:
- TOML: Rejected — not yet a project dependency, and YAML is already used extensively in the Kubernetes ecosystem.
- JSON: Rejected — no comment support, less human-friendly for configuration files.
- INI: Rejected — limited nesting, no list support, doesn't align with K8s ecosystem.

## R3: Remediation Hint Architecture

**Decision**: Add a `remediation` string attribute to `KubeRayError` base class. Populate it per-error-type with kubectl commands and documentation links.

**Rationale**: The simplest approach that meets FR-001 through FR-003. A plain string attribute is easy to access, display, and test. Structured remediation (list of steps, severity levels) is explicitly out of scope per the spec assumptions.

**Implementation pattern**:
```python
class KubeRayError(Exception):
    def __init__(self, message, remediation="", details=None):
        super().__init__(message)
        self.remediation = remediation
        self.details = details or {}
```

Each error subclass passes a default `remediation` string in its constructor.

**Alternatives considered**:
- Dataclass-based remediation object: Rejected — over-engineering for v1. Plain string is sufficient and can be upgraded later without breaking the API.
- Separate remediation registry: Rejected — adds indirection without clear benefit. Co-locating remediation with the error class is more maintainable.

## R4: Progress Callback Protocol

**Decision**: `progress_callback: Callable[[ProgressStatus], None] | None = None` parameter on wait methods.

**Rationale**: A simple callable that receives a `ProgressStatus` dataclass. No framework dependency, works in notebooks, scripts, and custom UIs.

**ProgressStatus fields**: `state` (str), `elapsed_seconds` (float), `message` (str), `metadata` (dict).

**Callback invocation**: Every poll cycle (5-10 seconds) during `wait_until_ready()` and `wait()`.

**Alternatives considered**:
- Event emitter pattern: Rejected — adds complexity, requires subscription management. A callback is simpler and satisfies the spec.
- `tqdm` integration: Rejected — adds a dependency for a narrow use case. Users who want tqdm can wrap the callback.
- Async generator / yield pattern: Rejected — changes the method signature fundamentally. A callback parameter is additive and preserves backward compatibility.

## R5: Retry Jitter Strategy

**Decision**: Full jitter with bounded maximum: `delay = random.uniform(0, backoff_factor * (2 ** (attempt - 1)))`, capped at 2x base delay.

**Rationale**: Full jitter is the AWS-recommended strategy for avoiding thundering herd. It provides maximum spread of retry times while keeping the expected delay at 50% of the exponential base.

**Implementation** (one-line change in `retry.py:69`):
```python
import random
delay = backoff_factor * (2 ** (attempt - 1))
delay = random.uniform(0, min(delay, delay * 2))  # Full jitter, bounded
```

**Alternatives considered**:
- Equal jitter (`delay/2 + random(0, delay/2)`): Rejected — less spread than full jitter, doesn't fully solve thundering herd.
- Decorrelated jitter: Rejected — more complex, requires state between retries. Full jitter is sufficient for the SDK's use case.
- No jitter (current): The thundering herd problem is documented in the spec.

## R6: Dry-Run Architecture

**Decision**: `dry_run=True` parameter on `create_cluster()`, `create_job()`, `create_service()`. Returns a `DryRunResult` object wrapping the CRD manifest dict.

**Rationale**: Local-only validation (pydantic model validation + `to_crd_dict()`) without making any Kubernetes API call. The `DryRunResult` wraps the dict and provides `to_yaml()` and `to_dict()` convenience methods.

**Implementation approach**: The existing model classes (`ClusterConfig`, `JobConfig`, `ServiceConfig`) already have `to_crd_dict()` methods. Dry-run mode simply validates the pydantic model, calls `to_crd_dict()`, and returns the result without calling the Kubernetes API.

**Alternatives considered**:
- Kubernetes server-side dry-run (`--dry-run=server`): Rejected — explicitly out of scope per spec assumptions. Requires API access and RBAC permissions.
- Separate `validate()` method: Partially adopted — validation happens implicitly during dry-run. A standalone `validate()` is not needed as a separate entry point.

## R7: Preset Design

**Decision**: Presets as a dictionary of `ClusterConfig` partial overrides, stored in a `presets.py` module. Users pass `preset="name"` to `create_cluster()`.

**Rationale**: Presets are opinionated defaults, not full configurations. They provide a base that users can override with explicit parameters. This matches the spec requirement (FR-020) that explicit parameters override preset values.

**Built-in presets** (minimum 3 per FR-018):
- `dev`: 1 worker, 1 CPU, 2Gi memory — lightweight development cluster
- `gpu-single`: 1 worker with 1 GPU, 4 CPU, 8Gi memory — single-GPU training
- `data-processing`: 4 workers, 2 CPU, 4Gi memory — multi-node data processing

**Alternatives considered**:
- YAML-based preset files: Rejected — adds file management complexity. Built-in Python dicts are simpler and version-controlled with the SDK.
- Enum-based presets: Rejected — less extensible and harder to inspect. Dictionary/dataclass approach allows listing presets with descriptions.

## R8: Compound Operations Design

**Decision**: Add `create_cluster_and_submit_job()` method on `KubeRayClient` that chains create → wait → submit.

**Rationale**: Covers the most common multi-step workflow (FR-022). Keeps the API surface small by providing one compound method rather than a generic chaining mechanism.

**Error handling**: On failure, the partially-created cluster is NOT deleted (FR-023). The error includes the cluster handle so users can inspect or clean up.

**Alternatives considered**:
- Builder/fluent API: Rejected — over-engineering per YAGNI principle. A single compound method is sufficient for the most common pattern.
- Pipeline abstraction: Rejected — generic pipeline adds complexity. The spec explicitly scopes this to one pattern.

## R9: CLI Output Formatting

**Decision**: Human-readable table format by default, `--output json` flag for machine-readable output.

**Rationale**: Matches kubectl UX convention. Tables are familiar to Kubernetes users. JSON output enables scripting and piping.

**Table implementation**: Use Python's `str.format()` or simple padding — no external table library needed. Tables are simple (3-5 columns) and don't need features like word wrapping or color.

**Alternatives considered**:
- `rich` tables: Rejected — adds a heavy dependency for cosmetic improvement. Simple formatted output is sufficient.
- `tabulate`: Rejected — unnecessary dependency. The tables are simple enough to format manually.

## R10: Capability Discovery Approach

**Decision**: `client.get_capabilities()` method that returns a `ClusterCapabilities` pydantic model.

**Rationale**: Queries the Kubernetes API for CRDs (KubeRay version), node labels (GPU detection), and CRD presence (Kueue, OpenShift). Gracefully handles RBAC errors by returning "unknown" for inaccessible capabilities (FR-031).

**Detection methods**:
- KubeRay: Check CRD existence + extract version from CRD annotations
- GPU: List nodes, check for `nvidia.com/gpu` resource
- Kueue: Check for `kueue.x-k8s.io` CRDs
- OpenShift: Check for `route.openshift.io` API group (reuses existing `platform/detection.py`)

**Alternatives considered**:
- Lazy detection on first use: Rejected — users want upfront discovery for conditional logic.
- Feature flags in config: Rejected — capabilities are cluster properties, not user preferences.

---

## US14 Addendum: Documentation Research (2026-02-24)

### R11: Documentation Gap Analysis

**Decision**: Update README, create new user guide page, create 8 example scripts, create CLI reference page.

**Rationale**: Auditing existing documentation reveals that none of the 8 new SDK features (dry-run, presets, progress callbacks, CLI, capability discovery, compound ops, config files, convenience imports) are documented in the README, user guide, or example scripts. The existing docs infrastructure (MkDocs + Material + mkdocstrings) is fully operational, so the work is purely content authoring.

**Current state**:
- README.md: Covers core features (handle API, clusters, jobs, services, OpenShift, Kueue, async, retry, auth). No mention of 8 new features.
- docs/user-guide/: 12 pages covering original features. Configuration page covers `SDKConfig` constructor only — no config file or env var docs.
- examples/: 7 scripts for original features. No scripts for new features.
- docs site nav: No entries for CLI reference or new feature documentation.

**Gap**:
- README needs 8 new sections (one per feature) with quick-start snippets
- docs site needs 2 new pages: `new-features.md` (user guide) and `cli-reference.md` (CLI reference)
- examples/ needs 8 new scripts (one per feature, standalone)
- mkdocs.yml nav needs 3 new entries

### R12: Example Script Standalone Strategy

**Decision**: Examples use dry-run mode, temporary config files, import validation, and commented annotations for cluster-dependent steps.

**Rationale**: Per clarification session, examples must run standalone without a live cluster. Features that inherently don't require a cluster (imports, config loading, dry-run, preset listing) run fully. Features that require a cluster (progress callbacks, compound ops, capability discovery, CLI commands) annotate those steps with `# NOTE: Requires a running KubeRay cluster` comments and demonstrate setup/config that works standalone.

**Standalone mapping**:
| Feature | Standalone? | Strategy |
|---------|-------------|----------|
| Convenience imports | Yes | Import and print types |
| Config file/env vars | Yes | Write temp config, set env vars, verify precedence |
| Dry-run mode | Yes | `dry_run=True` returns manifest without cluster |
| Presets | Yes | `list_presets()` + `dry_run=True` with preset |
| Progress callbacks | Partial | Define callback function; annotate `wait_until_ready()` call |
| Compound operations | Partial | Show method signature; annotate cluster-required step |
| Capability discovery | Partial | Show `get_capabilities()` usage; annotate cluster-required step |
| CLI tool | Partial | Python script using subprocess to show CLI commands; annotate cluster-required commands |

### R13: Version Annotation Format

**Decision**: Use italic text `*Added in v0.2.0*` after each feature heading in README and user guide.

**Rationale**: Consistent with Python library conventions (e.g., Python stdlib docs use "New in version X.Y"). Italic text is visually distinct but not intrusive. The version number corresponds to the release that includes the 004-sdk-ux-enhancements feature.

**Alternatives considered**:
- Badge/shield image: Rejected — heavyweight for inline doc annotations, adds image loading overhead.
- Admonition box: Rejected — too prominent for a version note; admonitions are for warnings and tips.

### R14: CLI Reference Page Structure

**Decision**: Dedicated MkDocs page at `docs/user-guide/cli-reference.md` with full command tree, options, and output examples.

**Rationale**: Per clarification session, the CLI reference lives on the docs site, not in the README. The README links to it. The page structure mirrors kubectl reference conventions: command tree overview, then per-subcommand sections with flags, examples, and sample output.

**Page structure**:
1. Overview (command tree diagram)
2. Global options (`--namespace`, `--output`, `--config`)
3. `kuberay cluster` subcommands (list, create, get, delete)
4. `kuberay job` subcommands (list, create, get, delete)
5. `kuberay service` subcommands (list, create, get, delete)
6. `kuberay capabilities` command
7. Output format examples (table vs JSON)
