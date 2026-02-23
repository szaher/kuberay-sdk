# Feature Specification: Automated Documentation Site

**Feature Branch**: `002-automated-docs-site`
**Created**: 2026-02-23
**Status**: Draft
**Input**: User description: "I want to create a comprehensive and thorough docs site in automated way. The docs site needs to be split between two users developer docs and user docs (AI engineer, data scientists, ML engineer, ray user, ...etc)"

## Clarifications

### Session 2026-02-23

- Q: Should guide pages be hand-authored markdown, auto-generated from code analysis, or hand-authored templates with auto-injected snippets? → A: Hand-authored markdown files built by the automated pipeline (standard approach). "Automated" refers to the build/publish pipeline and API reference generation, not to prose authoring.
- Q: Should versioned docs include a changelog or "What's New" page? → A: Yes, include a hand-authored "What's New" / changelog page in each versioned doc set, summarizing API changes from the previous version.
- Q: Should Python example scripts be rendered as full pages or just listed with download links? → A: Render as syntax-highlighted pages with the full source visible, plus a download link. This makes the inline comments searchable and browsable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — User Documentation: Getting Started and Guides (Priority: P1)

An AI engineer or data scientist discovers the kuberay-sdk package and visits the documentation site. They need to understand what the SDK does, how to install it, and how to perform common tasks — creating a Ray cluster, submitting a training job, deploying a Ray Serve application — without any Kubernetes expertise. The documentation walks them through installation, authentication setup, and progressively more complex workflows. Each guide contains runnable code examples they can copy-paste and adapt. The site is organized by task (e.g., "Cluster Management", "Job Submission", "Ray Serve") rather than by internal SDK structure.

**Why this priority**: User-facing documentation is the primary driver of SDK adoption. Without clear getting-started guides, users cannot onboard. This delivers standalone value even without developer docs.

**Independent Test**: Can be fully tested by building the docs site locally, navigating to the user guide section, and verifying all pages render correctly with working code examples, proper cross-links, and a searchable index.

**Acceptance Scenarios**:

1. **Given** a new user visits the docs site, **When** they navigate to the Getting Started section, **Then** they find installation instructions, authentication setup, and a working "Hello World" cluster creation example within the first two pages.
2. **Given** a data scientist wants to submit a training job, **When** they navigate to the Job Submission guide, **Then** they find step-by-step instructions with code examples covering both standalone RayJob and Dashboard submission modes.
3. **Given** an ML engineer wants to deploy a model via Ray Serve, **When** they navigate to the Ray Serve guide, **Then** they find instructions for creating a RayService, checking status, updating replicas, and retrieving the endpoint URL.
4. **Given** a user browses the docs site, **When** they use the search feature, **Then** they can find relevant pages by searching for terms like "cluster", "job logs", "storage volume", or "OpenShift".
5. **Given** a user reads any guide page, **When** they encounter a class or method name, **Then** that name links to the corresponding auto-generated API reference page.

---

### User Story 2 — Auto-Generated API Reference (Priority: P2)

A user who has completed the getting-started guides needs detailed API reference documentation — method signatures, parameter descriptions, return types, exception types, and usage examples. This reference is auto-generated from the Python source code docstrings so that it stays in sync with the codebase without manual maintenance. The reference covers all public classes (KubeRayClient, AsyncKubeRayClient, all Handle classes, all model classes, error classes, and platform functions). Each class and method page includes the docstring, type annotations, default values, and cross-links to related classes.

**Why this priority**: API reference is the most-consulted section after initial onboarding. Auto-generation ensures accuracy and eliminates documentation drift. This must exist for users to move beyond guided tutorials into self-directed usage.

**Independent Test**: Can be tested by running the documentation build command and verifying that every public class and method listed in `__init__.py` exports has a corresponding API reference page with signature, docstring, and cross-links.

**Acceptance Scenarios**:

1. **Given** a developer changes a docstring in the source code, **When** the documentation site is rebuilt, **Then** the API reference page reflects the updated docstring without any manual editing of documentation files.
2. **Given** a user visits the API reference for `KubeRayClient`, **When** they view the `create_cluster` method, **Then** they see the full method signature with parameter types, defaults, return type (`ClusterHandle`), possible exceptions, and a usage example.
3. **Given** a user views the API reference for `ClusterStatus`, **When** they look at the `state` field, **Then** they see it is of type `ClusterState` with a link to the enum values (CREATING, RUNNING, SUSPENDED, FAILED, DELETING, UNKNOWN).
4. **Given** a user views any Handle method, **When** that method can raise exceptions, **Then** the Raises section lists each exception class with a link to the error reference.

---

### User Story 3 — Developer/Contributor Documentation (Priority: P3)

A developer who wants to contribute to the kuberay-sdk project visits the documentation site and finds a dedicated "Developer Guide" section. This section explains the architecture (module structure, Handle pattern, CRD generation, Dashboard API client), development setup (clone, install dev dependencies, run tests), testing conventions (unit, contract, integration test categories), code style requirements (ruff, mypy), and contribution workflow (branch naming, commit conventions, PR process). The developer can set up a working development environment and run all tests by following the guide.

**Why this priority**: Contributor documentation enables community participation and reduces onboarding friction for new developers. It depends on the user docs site infrastructure being in place (P1) but is lower priority than end-user documentation.

**Independent Test**: Can be tested by having a new contributor follow the developer guide from scratch — clone the repo, set up the development environment, run tests, and understand the architecture — without needing external help.

**Acceptance Scenarios**:

1. **Given** a new contributor visits the Developer Guide, **When** they follow the "Development Setup" page, **Then** they can successfully install all dev dependencies, run the test suite, and see all tests pass.
2. **Given** a developer reads the Architecture page, **When** they want to understand how cluster creation works end-to-end, **Then** they find a description of the flow from `KubeRayClient.create_cluster()` through `ClusterService` to the Kubernetes API, including the role of models, services, and handles.
3. **Given** a developer wants to add a new feature, **When** they read the Contributing page, **Then** they understand the testing requirements (unit, contract, integration), code style rules (ruff, mypy strict mode), and how to run validation before submitting a PR.

---

### User Story 4 — Automated Build and Deployment Pipeline (Priority: P4)

A maintainer wants the documentation site to be built and published automatically whenever changes are made to the codebase. The build process extracts API reference from source code docstrings, combines it with hand-written guide pages, and produces a static site. The build can run locally for preview during development and in a CI pipeline for automated publishing. The build fails if there are broken cross-links, missing API reference pages, or rendering errors, providing early feedback to contributors.

**Why this priority**: Automation ensures documentation stays current with every code change. Without it, docs drift out of sync with the code. This story formalizes the build and validation pipeline.

**Independent Test**: Can be tested by running the docs build command locally, verifying it completes without errors, produces a navigable static site, and catches intentionally introduced broken links.

**Acceptance Scenarios**:

1. **Given** a contributor modifies source code or documentation files, **When** they run the docs build command locally, **Then** the site builds successfully and they can preview it in a browser.
2. **Given** a contributor introduces a broken cross-link in a guide page, **When** the docs build runs, **Then** the build fails with a clear error message identifying the broken link and its location.
3. **Given** a new public class is added to the SDK without updating the docs, **When** the docs build runs, **Then** the API reference is automatically generated for the new class from its docstrings.
4. **Given** a PR is merged to the main branch, **When** the CI pipeline runs, **Then** the documentation site is rebuilt and published to the hosting destination.

---

### User Story 5 — Versioned Documentation (Priority: P5)

A user working with a specific version of kuberay-sdk (e.g., 0.1.0) needs to view the documentation that matches their installed version, not the latest development version. The documentation site supports version switching, allowing users to select their SDK version from a dropdown and see documentation that matches the API available in that release. The latest stable version is shown by default, with a "development" version available for unreleased changes.

**Why this priority**: Version-specific docs prevent user confusion when APIs change between releases. Lower priority than the initial docs site because versioning only matters once there are multiple released versions.

**Independent Test**: Can be tested by creating two version tags, building docs for each, and verifying that the version switcher correctly navigates between them with different content.

**Acceptance Scenarios**:

1. **Given** a user visits the docs site, **When** they see the version selector, **Then** it defaults to the latest stable release version.
2. **Given** a user is viewing docs for version 0.1.0, **When** they switch to version 0.2.0, **Then** the content updates to reflect the API available in 0.2.0 (including any new methods, changed parameters, or deprecated features).
3. **Given** the project has unreleased changes on the main branch, **When** a user selects the "dev" version in the version switcher, **Then** they see documentation matching the current development code.
4. **Given** a user has upgraded from v0.1.0 to v0.2.0, **When** they navigate to the "What's New" page for v0.2.0, **Then** they find a summary of new features, changed APIs, and deprecations since v0.1.0.

---

### User Story 6 — Notebook Examples Gallery (Priority: P6)

A data scientist or ML engineer prefers learning through interactive Jupyter notebooks rather than static documentation. The docs site includes a gallery of runnable notebook examples (e.g., MNIST distributed training, model serving, cluster autoscaling). Each notebook in the gallery shows a rendered preview on the docs site with a download link to the `.ipynb` file. The gallery is auto-generated from notebook files in the repository — adding a new notebook to the designated directory automatically includes it in the gallery on the next build.

**Why this priority**: Notebooks are the preferred medium for the primary user audience (data scientists, ML engineers). Lower priority because static guides (P1) serve the same educational purpose, but notebooks add significant value for the target audience.

**Independent Test**: Can be tested by placing a notebook in the examples directory, building the docs site, and verifying the notebook appears rendered in the gallery with a download link.

**Acceptance Scenarios**:

1. **Given** a data scientist visits the examples gallery, **When** they browse the available notebooks, **Then** they see a list of notebook examples with titles, descriptions, and rendered previews.
2. **Given** a user views a notebook example page, **When** they want to run the notebook locally, **Then** they can download the `.ipynb` file via a download link on the page.
3. **Given** a contributor adds a new `.ipynb` file to the examples directory, **When** the docs site is rebuilt, **Then** the new notebook automatically appears in the gallery without any manual index file updates.

---

### Edge Cases

- What happens when a public class has no docstring? The build must still generate an API reference page with the class name and method signatures, and emit a warning during the build.
- What happens when a code example in a guide page references a class that was removed in a newer version? The build must detect broken cross-links and fail with an actionable error.
- What happens when the docs site is built on a system without the SDK's runtime dependencies installed? The build must still succeed for documentation generation (API reference extraction should work without importing the full dependency tree).
- How does the site handle users navigating to a page URL that existed in a previous version but was removed? The site should show a 404 page with a suggestion to check the version selector or search.
- What happens when a notebook contains outputs with large images or binary data? The rendered preview must handle these gracefully without bloating the page load time (e.g., lazy loading or thumbnails).

## Requirements *(mandatory)*

### Functional Requirements

#### Site Structure and Navigation

- **FR-001**: The documentation site MUST have two clearly separated top-level sections: "User Guide" (for AI engineers, data scientists, ML engineers, Ray users) and "Developer Guide" (for SDK contributors).
- **FR-002**: The site MUST include a global navigation bar with links to: User Guide, Developer Guide, API Reference, Examples, and a version selector.
- **FR-003**: The site MUST include full-text search across all pages with results ranked by relevance.
- **FR-004**: The site MUST render as a responsive static site viewable on desktop and tablet browsers.

#### User Guide Content

- **FR-005**: The User Guide MUST include a "Getting Started" section with installation instructions, prerequisites (Python version, Kubernetes cluster, KubeRay operator), and authentication setup via kube-authkit.
- **FR-006**: The User Guide MUST include a "Quick Start" page demonstrating the three most common operations (create cluster, submit job, deploy service) with copy-pasteable code examples.
- **FR-007**: The User Guide MUST include a "Cluster Management" guide covering creation with simple parameters, creation with advanced parameters (worker groups, head node config), scaling, monitoring, and deletion.
- **FR-008**: The User Guide MUST include a "Job Submission" guide covering standalone RayJob (CRD mode), Dashboard submission to running clusters, runtime environment configuration, log streaming, and job lifecycle management.
- **FR-009**: The User Guide MUST include a "Ray Serve" guide covering service creation, status monitoring, replica updates, endpoint access, and heterogeneous worker groups for agentic workloads.
- **FR-010**: The User Guide MUST include a "Storage and Runtime Environment" guide covering PVC attachment (new and existing), pip/conda dependency installation, environment variables, and working directory configuration.
- **FR-011**: The User Guide MUST include an "OpenShift Integration" guide covering hardware profiles, Kueue queue integration, Route auto-creation, and platform detection.
- **FR-012**: The User Guide MUST include an "Experiment Tracking" guide covering MLflow integration via the `ExperimentTracking` model.
- **FR-013**: The User Guide MUST include an "Async Usage" guide demonstrating the `AsyncKubeRayClient` with async/await patterns.
- **FR-014**: The User Guide MUST include an "Error Handling" guide explaining the error hierarchy, common error scenarios, and recovery patterns.
- **FR-015**: The User Guide MUST include a "Configuration" reference documenting all `SDKConfig` fields, namespace resolution behavior, and authentication options.

#### API Reference

- **FR-016**: The API reference MUST be auto-generated from Python source code docstrings and type annotations on every build.
- **FR-017**: The API reference MUST cover every public class, method, function, and constant exported from the `kuberay_sdk` package (as declared in `__init__.py`).
- **FR-018**: Each API reference entry MUST display: the fully qualified name, the method/function signature with type annotations, parameter descriptions, return type, raised exceptions, and the docstring including any embedded usage examples.
- **FR-019**: The API reference MUST include cross-links between related classes (e.g., `ClusterHandle.status()` links to `ClusterStatus`, `ClusterStatus.state` links to `ClusterState` enum).
- **FR-020**: The API reference MUST organize classes into logical groupings: Client classes, Handle classes, Model classes, Error classes, Platform utilities.

#### Developer Guide Content

- **FR-021**: The Developer Guide MUST include an "Architecture" page describing the module structure (`models/`, `services/`, `platform/`), the Handle pattern, CRD generation flow, and the Dashboard API client.
- **FR-022**: The Developer Guide MUST include a "Development Setup" page with instructions to clone the repository, create a virtual environment, install dev dependencies, and verify the setup by running the test suite.
- **FR-023**: The Developer Guide MUST include a "Testing" page describing the three test categories (unit, contract, integration), test file conventions, shared fixtures, and how to run tests selectively.
- **FR-024**: The Developer Guide MUST include a "Code Style" page documenting ruff configuration, mypy strict mode requirements, and docstring conventions.
- **FR-025**: The Developer Guide MUST include a "Contributing" page describing the branch naming convention, commit conventions, PR process, and required checks (ruff, mypy, tests pass).

#### Examples and Notebooks

- **FR-026**: The documentation site MUST include a rendered examples gallery page listing all example scripts and notebooks with titles and one-line descriptions.
- **FR-027**: Jupyter notebooks in the examples directory MUST be rendered as static HTML pages in the docs site with code cells, outputs, and markdown cells preserved.
- **FR-028**: Python example scripts in the examples directory MUST be rendered as syntax-highlighted pages with the full source code visible, making inline comments searchable and browsable.
- **FR-029**: Each example page (script or notebook) MUST include a download link for the original source file (`.py` or `.ipynb`).

#### Automation and Build

- **FR-030**: The documentation site MUST be buildable from a single command run at the repository root.
- **FR-031**: The build process MUST auto-generate API reference pages from the current source code on every run, without manual intermediate steps.
- **FR-032**: The build process MUST validate all internal cross-links and fail with an error listing broken links if any are found.
- **FR-033**: The build process MUST be runnable locally for preview during development (local dev server with hot reload).
- **FR-034**: The documentation site MUST support version-specific builds, allowing multiple versions to coexist at different URL paths (e.g., `/v0.1.0/`, `/v0.2.0/`, `/latest/`).
- **FR-035**: Each versioned doc set MUST include a hand-authored "What's New" / changelog page summarizing new features, changed APIs, and deprecations since the previous version.

#### Content Quality

- **FR-036**: Every guide page MUST include at least one runnable code example.
- **FR-037**: Code examples in guide pages MUST use syntax highlighting appropriate to the language (Python).
- **FR-038**: The documentation site MUST include a 404 page that suggests using the search feature or version selector.

### Key Entities

- **Page**: A single documentation page with a title, content (markdown), section assignment (User Guide, Developer Guide, API Reference, Examples), and optional version tag.
- **Section**: A top-level grouping of pages (User Guide, Developer Guide, API Reference, Examples) with a navigation hierarchy.
- **API Entry**: An auto-generated documentation entry for a public Python symbol (class, method, function, constant) with signature, docstring, type annotations, and cross-links.
- **Example**: A runnable code sample (Python script or Jupyter notebook) with a title, description, rendered preview, and download link.
- **Version**: A labeled snapshot of the documentation tied to a release tag, with a URL path prefix and entry in the version selector.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can find installation instructions and create their first Ray cluster by following the docs in under 10 minutes, starting from the docs site landing page.
- **SC-002**: 100% of public classes and methods exported from `kuberay_sdk.__init__` have auto-generated API reference pages with signatures, docstrings, and type annotations.
- **SC-003**: The documentation site builds from a single command in under 60 seconds on a standard developer machine.
- **SC-004**: All internal cross-links between guide pages and API reference pages resolve successfully — zero broken links on every build.
- **SC-005**: The documentation site is searchable, returning relevant results for at least 90% of SDK feature terms (e.g., "cluster", "job logs", "storage volume", "RuntimeEnv", "OpenShift").
- **SC-006**: A new contributor can set up a development environment and run the test suite by following the Developer Guide in under 15 minutes.
- **SC-007**: Adding a new notebook to the examples directory automatically includes it in the gallery on the next build with no manual index edits.
- **SC-008**: Changing a docstring in the source code is reflected in the API reference on the next build with no manual editing of documentation files.

## Assumptions

- The SDK's existing docstrings are comprehensive enough to serve as the basis for API reference generation. The codebase has been verified to have docstrings with examples on all public classes and methods.
- Guide pages (User Guide and Developer Guide) are hand-authored markdown files. The "automated" aspect refers to the build pipeline (API reference generation, notebook rendering, link validation, CI publishing), not to prose content generation.
- The existing README.md content (overview, quick start, advanced usage) can be refactored into individual guide pages rather than written from scratch.
- The existing 6 example scripts and 1 Jupyter notebook in `examples/` will be the initial content for the examples gallery.
- The documentation hosting destination (e.g., GitHub Pages, ReadTheDocs) will be determined during the planning phase; the spec is agnostic to hosting platform.
- The build process will use the project's existing Python virtual environment and dev dependencies.
- Version tagging follows semantic versioning as declared in `pyproject.toml`.

## Out of Scope

- Internationalization/localization — the docs site will be English only.
- User authentication or gated access — the docs site is public.
- Interactive API playground or live code execution — examples are static code blocks.
- PDF or EPUB export of documentation.
- Analytics or usage tracking on the docs site.
- Writing new example scripts or notebooks beyond what already exists in the repository (the site surfaces existing examples).
