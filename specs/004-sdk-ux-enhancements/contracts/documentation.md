# Contract: Comprehensive Feature Documentation (US14)

**Feature**: 004-sdk-ux-enhancements
**Date**: 2026-02-24
**Requirements**: FR-034, FR-035, FR-036, FR-037, SC-013, SC-014

## README Contract

### Required Sections (FR-034)

Each section MUST appear in `README.md` after the existing "Async Client" section, in this order:

1. **Convenience Imports** — demonstrates `from kuberay_sdk import WorkerGroup, RuntimeEnv, StorageVolume`
2. **Configuration File & Environment Variables** — shows `~/.kuberay/config.yaml` schema, `KUBERAY_*` env vars, precedence order, credential warning
3. **Dry-Run Mode** — shows `create_cluster(..., dry_run=True)` and `result.to_yaml()`
4. **Presets** — shows `preset="dev"` and `list_presets()`
5. **Progress Callbacks** — shows `wait_until_ready(progress_callback=...)`
6. **Compound Operations** — shows `create_cluster_and_submit_job()`
7. **Capability Discovery** — shows `client.get_capabilities()`
8. **CLI Tool** — shows `kuberay cluster list` and links to CLI reference page

### Section Format

```markdown
### <Feature Name>

*Added in v0.2.0*

<1-2 sentence description.>

​```python
<Runnable code snippet>
​```
```

### Credential Warning (FR-036)

The Configuration File section MUST include:

```markdown
> **Security note**: The config file stores operational settings only (namespace, timeout, retry).
> Do NOT store credentials or auth tokens in this file.
> Authentication is handled by kubeconfig and [kube-authkit](https://pypi.org/project/kube-authkit/).
```

## User Guide Page Contract

### New Features Page (`docs/user-guide/new-features.md`)

Structure:

```markdown
# New Features

Overview paragraph listing all 8 features.

## Convenience Imports
*Added in v0.2.0*
[Detailed usage, before/after comparison, list of re-exported types]

## Configuration File & Environment Variables
*Added in v0.2.0*
[Config file schema, env vars table, precedence diagram, credential warning, examples]

## Dry-Run Mode
*Added in v0.2.0*
[Usage, to_yaml(), to_dict(), validation errors, async support]

## Presets
*Added in v0.2.0*
[Built-in presets table, custom usage, override behavior]

## Progress Callbacks
*Added in v0.2.0*
[Callback signature, ProgressStatus fields, notebook usage, custom callbacks]

## Compound Operations
*Added in v0.2.0*
[Method signature, error handling, partial failure behavior]

## Capability Discovery
*Added in v0.2.0*
[get_capabilities() usage, ClusterCapabilities fields, conditional logic examples]

## CLI Tool
*Added in v0.2.0*
[Quick overview, link to CLI Reference page]
```

### CLI Reference Page (`docs/user-guide/cli-reference.md`)

Structure:

```markdown
# CLI Reference

## Overview
Command tree diagram.

## Global Options
--namespace, --output, --config

## kuberay cluster
### kuberay cluster list
### kuberay cluster create
### kuberay cluster get
### kuberay cluster delete

## kuberay job
### kuberay job list
### kuberay job create
### kuberay job get
### kuberay job delete

## kuberay service
### kuberay service list
### kuberay service create
### kuberay service get
### kuberay service delete

## kuberay capabilities

## Output Formats
Table vs JSON examples.
```

Each subcommand section MUST include:
- Synopsis: `kuberay <resource> <action> [OPTIONS]`
- Options table: flag, type, default, description
- Example: command + sample output (table and JSON)

## Example Scripts Contract (FR-035, SC-014)

### Requirements

1. Each script MUST have a module-level docstring explaining the feature
2. Each script MUST use `if __name__ == "__main__":` guard
3. Each script MUST be runnable standalone where possible (dry-run, imports, config)
4. Cluster-dependent steps MUST be annotated: `# NOTE: Requires a running KubeRay cluster`
5. Each script MUST include inline comments explaining each step
6. All scripts MUST pass `ruff check examples/` (SC-014)

### Script Template

```python
"""<Feature Name> Example

Demonstrates <what this script shows>.

<Feature description and when to use it.>

Added in v0.2.0.
"""

from kuberay_sdk import KubeRayClient  # and other imports


def main() -> None:
    """<Brief description of what main does>."""
    # Step 1: <description>
    ...

    # Step 2: <description>
    ...


if __name__ == "__main__":
    main()
```

## MkDocs Navigation Contract

New entries to add to `mkdocs.yml` nav:

```yaml
nav:
  - User Guide:
      # ... existing entries ...
      - Configuration: user-guide/configuration.md
      - New Features: user-guide/new-features.md          # NEW
      - CLI Reference: user-guide/cli-reference.md        # NEW
      - Migration Guide: user-guide/migration.md
      - Troubleshooting: user-guide/troubleshooting.md
  - Examples:
      # ... existing entries ...
      - Dry-Run Preview: examples/dry-run-preview.md      # NEW (or link to script)
      - Presets: examples/presets-usage.md                 # NEW
      - Progress Callbacks: examples/progress-callbacks.md # NEW
      - CLI Usage: examples/cli-usage.md                   # NEW
      - Capability Discovery: examples/capability-discovery.md  # NEW
      - Compound Operations: examples/compound-operations.md    # NEW
      - Config & Env Vars: examples/config-env-vars.md          # NEW
      - Convenience Imports: examples/convenience-imports.md    # NEW
```

## Validation Checklist

- [ ] All 8 features documented in README with code snippets (SC-013)
- [ ] Version annotations on all new feature sections (clarification)
- [ ] Config precedence diagram with credential warning (FR-036)
- [ ] CLI reference on dedicated docs page, README links to it (FR-037, clarification)
- [ ] 8 example scripts pass `ruff check examples/` (SC-014)
- [ ] Example scripts are standalone where possible (clarification)
- [ ] MkDocs nav updated with new pages
- [ ] No broken cross-links
- [ ] User guide page created as new docs site page (clarification)
