<!--
Sync Impact Report
===================
Version change: N/A → 1.0.0
Added principles:
  - I. API-First Design (new)
  - II. User-Centric Abstraction (new)
  - III. Progressive Disclosure (new)
  - IV. Test-First (new)
  - V. Simplicity & YAGNI (new)
Added sections:
  - Tech Stack & Constraints (new)
  - Development Workflow (new)
  - Governance (new)
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed
    (Constitution Check section is generic; will reference these
    principles at plan-generation time)
  - .specify/templates/spec-template.md ✅ no changes needed
    (spec template is domain-agnostic)
  - .specify/templates/tasks-template.md ✅ no changes needed
    (task categorization is generic)
Follow-up TODOs: none
-->

# KubeRay Python SDK Constitution

## Core Principles

### I. API-First Design

All features MUST begin as explicit API contracts — type
definitions, function signatures, and interface protocols —
before any implementation work starts.

- Public surface area MUST be defined in type stubs or
  abstract base classes and reviewed before coding begins.
- Every public function and class MUST include docstrings
  with usage examples.
- Breaking changes to the public API MUST follow semantic
  versioning and MUST be documented in a changelog.

**Rationale**: An SDK lives or dies by its API. Defining
contracts first prevents accidental complexity leaking into
the user-facing surface and enables parallel work on
implementation and documentation.

### II. User-Centric Abstraction

The SDK MUST hide Kubernetes complexity from its primary
users — data scientists, AI/ML practitioners, and AI
engineers. Users MUST be able to create Ray clusters,
create Ray jobs, and submit Ray jobs to existing clusters
without understanding Kubernetes concepts.

- Default workflows MUST NOT require users to write or
  read Kubernetes manifests, know about Pods, Services,
  or CRDs.
- Namespace awareness MUST be handled transparently via
  configuration or context, not by requiring users to
  pass namespace parameters everywhere.
- Authentication MUST use kube-authkit and MUST be
  configured once, not per-call.
- Error messages MUST be expressed in Ray/ML domain terms
  (e.g., "cluster failed to start") not Kubernetes terms
  (e.g., "Pod CrashLoopBackOff").

**Rationale**: The target audience cares about running Ray
workloads, not operating Kubernetes. Leaking infrastructure
details into the SDK defeats its purpose.

### III. Progressive Disclosure

Advanced Kubernetes capabilities — Kueue integration,
scheduling constraints via labels and annotations, resource
quotas, tolerations, node affinity — MUST be accessible
but MUST NOT be required for basic usage.

- The SDK MUST provide a layered API: simple defaults for
  common cases, optional parameters for advanced tuning.
- Advanced options MUST use keyword arguments or builder
  patterns, never positional arguments.
- Documentation MUST clearly separate "Getting Started"
  (no K8s knowledge) from "Advanced Configuration"
  (K8s-aware users).

**Rationale**: Some users are platform engineers who need
fine-grained control. Blocking them forces workarounds.
Exposing everything by default overwhelms data scientists.
Progressive disclosure satisfies both audiences.

### IV. Test-First (NON-NEGOTIABLE)

All features MUST follow Test-Driven Development: tests
are written first, confirmed to fail, then implementation
makes them pass.

- Red-Green-Refactor cycle MUST be strictly followed.
- Unit tests MUST cover all public API methods.
- Integration tests MUST validate end-to-end workflows
  against a KubeRay-enabled cluster (real or mocked).
- Contract tests MUST verify that SDK-generated Kubernetes
  resources match expected KubeRay CRD schemas.

**Rationale**: An SDK is a contract with its users. TDD
ensures the contract is defined before implementation and
prevents regressions that break downstream applications.

### V. Simplicity & YAGNI

Every feature, abstraction, and configuration option MUST
justify its existence with a concrete current use case.

- MUST NOT add features "for future use" or "just in case."
- Prefer fewer, composable primitives over many specialized
  helpers.
- Three similar lines of code are better than a premature
  abstraction.
- Configuration MUST use sensible defaults; users MUST be
  able to create a basic Ray cluster with minimal parameters.

**Rationale**: SDKs accumulate complexity over time. Strict
YAGNI discipline keeps the surface area small, learning
curve short, and maintenance burden manageable.

## Tech Stack & Constraints

- **Language**: Python 3.10+
- **Kubernetes Client**: official `kubernetes` Python client
- **Authentication**: kube-authkit
- **Target Platform**: Any environment with kubeconfig access
  to a Kubernetes cluster running the KubeRay operator
- **Packaging**: distributed as a pip-installable package
- **Dependencies**: MUST be kept minimal; every new
  dependency MUST be justified
- **Compatibility**: MUST support the two most recent
  KubeRay operator minor versions

## Development Workflow

- All code changes MUST be submitted via pull requests.
- Pull requests MUST include tests that pass before merge.
- Pull requests MUST pass linting (ruff) and type checking
  (mypy or pyright) in CI.
- Public API changes MUST include updated docstrings and
  usage examples.
- Commit messages MUST follow Conventional Commits format.
- Releases MUST follow semantic versioning (MAJOR.MINOR.PATCH).

## Governance

This constitution is the authoritative source of project
principles and development standards. It supersedes all
other guidance when conflicts arise.

- **Amendments**: Any change to this constitution MUST be
  proposed via pull request, reviewed by at least one
  maintainer, and include a migration plan if existing code
  is affected.
- **Versioning**: Constitution versions follow semantic
  versioning — MAJOR for principle removals or redefinitions,
  MINOR for new principles or material expansions, PATCH
  for clarifications and typo fixes.
- **Compliance**: All pull requests and code reviews MUST
  verify adherence to these principles. Deviations MUST be
  explicitly justified and documented.

**Version**: 1.0.1 | **Ratified**: 2026-02-23 | **Last Amended**: 2026-02-23
