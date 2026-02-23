# Tasks: Automated Documentation Site

**Input**: Design documents from `/specs/002-automated-docs-site/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/build_interface.md, quickstart.md

**Tests**: No test tasks generated — not explicitly requested in the feature specification. Build validation (`mkdocs build --strict`) serves as the test suite per plan.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — documentation dependencies, directory structure, and central configuration

- [x] T001 Create documentation directory structure: `docs/user-guide/getting-started/`, `docs/developer-guide/`, `docs/examples/`, `docs/overrides/`, `scripts/`, `.github/workflows/`
- [x] T002 Add documentation dependencies to `[docs]` optional group in `pyproject.toml`: mkdocs (1.6.x), mkdocs-material (9.7.x), mkdocstrings[python] (1.0.x), mkdocs-gen-files (0.6.x), mkdocs-literate-nav (0.6.x), mkdocs-section-index (0.3.x), mkdocs-jupyter (0.25.x), mike (2.1.x)
- [x] T003 Create `mkdocs.yml` at repository root with full configuration: site metadata, Material theme (palette, features, icons), plugins (search, mkdocstrings, gen-files, literate-nav, section-index, mkdocs-jupyter), markdown extensions (admonitions, code highlighting, content tabs, pymdownx.snippets), and complete nav structure for all sections

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared pages and build scripts that MUST exist before any user story content can be added

**Warning**: No user story work can begin until this phase is complete

- [x] T004 [P] Create `docs/index.md` landing page with project overview, feature highlights, and navigation links to User Guide, Developer Guide, API Reference, and Examples sections
- [x] T005 [P] Create `docs/404.md` custom 404 page with "Page not found" message, link to search feature, link to version selector, and link to site home page (FR-038)
- [x] T006 Create `scripts/gen_ref_pages.py` build script to walk `src/kuberay_sdk/`, generate virtual markdown pages with `:::` directives for each module, and produce `reference/SUMMARY.md` for literate-nav (FR-016, FR-017, FR-031)

**Checkpoint**: Foundation ready — directory structure exists, mkdocs.yml configured, landing page and 404 page created, API reference generation script ready. User story content can now be added.

---

## Phase 3: User Story 1 — User Documentation: Getting Started and Guides (Priority: P1) MVP

**Goal**: Deliver complete user-facing documentation covering installation, quick start, and all SDK feature guides. Enables AI engineers and data scientists to onboard without Kubernetes expertise.

**Independent Test**: Run `mkdocs build --strict`, navigate to the User Guide section, verify all 11 pages render with working code examples, proper syntax highlighting, and cross-links to API reference pages.

### Implementation for User Story 1

- [x] T007 [P] [US1] Create `docs/user-guide/getting-started/installation.md` with prerequisites (Python 3.10+, K8s cluster, KubeRay operator), pip install command, kube-authkit authentication setup, and verification steps (FR-005)
- [x] T008 [P] [US1] Create `docs/user-guide/getting-started/quick-start.md` with three core operations: create cluster, submit job, deploy Ray Serve app — each with copy-pasteable code examples (FR-006)
- [x] T009 [P] [US1] Create `docs/user-guide/cluster-management.md` covering cluster creation (simple and advanced parameters), worker groups, head node config, scaling, monitoring status, and deletion (FR-007)
- [x] T010 [P] [US1] Create `docs/user-guide/job-submission.md` covering standalone RayJob (CRD mode), Dashboard submission to running clusters, runtime env config, log streaming, and job lifecycle management (FR-008)
- [x] T011 [P] [US1] Create `docs/user-guide/ray-serve.md` covering RayService creation, status monitoring, replica updates, endpoint access, and heterogeneous worker groups for agentic workloads (FR-009)
- [x] T012 [P] [US1] Create `docs/user-guide/storage-runtime-env.md` covering PVC attachment (new and existing), pip/conda dependency installation, environment variables, and working directory configuration (FR-010)
- [x] T013 [P] [US1] Create `docs/user-guide/openshift.md` covering hardware profiles, Kueue queue integration, Route auto-creation, and platform detection (FR-011)
- [x] T014 [P] [US1] Create `docs/user-guide/experiment-tracking.md` covering MLflow integration via the ExperimentTracking model (FR-012)
- [x] T015 [P] [US1] Create `docs/user-guide/async-usage.md` demonstrating AsyncKubeRayClient with async/await patterns, concurrent operations, and error handling in async context (FR-013)
- [x] T016 [P] [US1] Create `docs/user-guide/error-handling.md` explaining the error hierarchy (KubeRayError, ClusterError, JobError, etc.), common error scenarios, translate_k8s_error, and recovery patterns (FR-014)
- [x] T017 [P] [US1] Create `docs/user-guide/configuration.md` documenting all SDKConfig fields, namespace resolution behavior, authentication options, and environment variable overrides (FR-015)

**Checkpoint**: All 11 User Guide pages exist. `mkdocs build --strict` passes for user guide section. Users can navigate getting-started through advanced guides with code examples on every page (FR-036, FR-037).

---

## Phase 4: User Story 2 — Auto-Generated API Reference (Priority: P2)

**Goal**: Deliver auto-generated API reference from Python docstrings and type annotations. Every public class, method, and constant in `kuberay_sdk` has a reference page with signature, docstring, cross-links, and examples.

**Independent Test**: Run `mkdocs build --strict`, verify every symbol exported from `kuberay_sdk.__init__` has a corresponding page under `site/reference/` with method signatures, type annotations, docstrings, and cross-links.

### Implementation for User Story 2

- [x] T018 [US2] Configure mkdocstrings handler options in `mkdocs.yml` for Google docstring style, show_source, show_signature_annotations, cross-reference linking, and logical grouping (Client, Handle, Model, Error, Platform classes) (FR-018, FR-019, FR-020)
- [x] T019 [US2] Verify and refine `scripts/gen_ref_pages.py` to correctly discover all public modules under `src/kuberay_sdk/`, generate `::: kuberay_sdk.module` directives, and produce a `SUMMARY.md` navigation file matching the reference/ site structure from contracts/build_interface.md (FR-016, FR-017)
- [x] T020 [US2] Run `mkdocs build --strict` and validate that API reference pages are generated for all exports in `kuberay_sdk.__init__.py` — fix any missing docstring warnings or broken cross-references (FR-017, FR-019)

**Checkpoint**: API reference is fully auto-generated. Changing a docstring in source code is reflected on the next build (SC-008). All public symbols have reference pages (SC-002).

---

## Phase 5: User Story 3 — Developer/Contributor Documentation (Priority: P3)

**Goal**: Deliver a Developer Guide section enabling new contributors to understand the architecture, set up a dev environment, run tests, follow code style conventions, and submit PRs.

**Independent Test**: A new contributor can follow the Developer Guide from clone to running tests without external help. `mkdocs build --strict` passes for developer guide section.

### Implementation for User Story 3

- [x] T021 [P] [US3] Create `docs/developer-guide/architecture.md` describing module structure (models/, services/, platform/), Handle pattern, CRD generation flow, Dashboard API client, and end-to-end flow diagrams (FR-021)
- [x] T022 [P] [US3] Create `docs/developer-guide/development-setup.md` with clone, venv creation, `pip install -e ".[dev]"` install, and test suite verification instructions (FR-022)
- [x] T023 [P] [US3] Create `docs/developer-guide/testing.md` describing unit/contract/integration test categories, test file conventions, shared fixtures, selective test running, and coverage expectations (FR-023)
- [x] T024 [P] [US3] Create `docs/developer-guide/code-style.md` documenting ruff configuration, mypy strict mode, docstring conventions (Google style), and import ordering rules (FR-024)
- [x] T025 [P] [US3] Create `docs/developer-guide/contributing.md` with branch naming convention, commit message format, PR process, required CI checks (ruff, mypy, tests), and review guidelines (FR-025)

**Checkpoint**: All 5 Developer Guide pages exist. A new contributor can set up a dev environment and run tests following the guide (SC-006).

---

## Phase 6: User Story 4 — Automated Build and Deployment Pipeline (Priority: P4)

**Goal**: Deliver a GitHub Actions CI pipeline that builds docs on every PR (validation) and deploys to GitHub Pages on merge to main. Contributors get early feedback on broken docs.

**Independent Test**: Push a PR with a docs change and verify the CI workflow runs `mkdocs build --strict` and reports pass/fail. Merge to main and verify site deploys to GitHub Pages.

### Implementation for User Story 4

- [x] T026 [US4] Create `.github/workflows/docs.yml` GitHub Actions workflow with: checkout, Python setup, `pip install -e ".[docs]"`, `mkdocs build --strict` on PR (validation), and `mike deploy --push` on main branch merge (deploy) (FR-030, FR-032, FR-033)
- [x] T027 [US4] Validate the CI pipeline catches broken links by temporarily introducing a broken cross-link, running `mkdocs build --strict`, and confirming the build fails with an actionable error message (FR-032)

**Checkpoint**: CI pipeline validates docs on every PR and deploys on merge. Build completes in under 60 seconds (SC-003).

---

## Phase 7: User Story 5 — Versioned Documentation (Priority: P5)

**Goal**: Deliver versioned documentation with a version selector dropdown. Multiple versions coexist at different URL paths. Latest stable is the default.

**Independent Test**: Deploy two versions via mike, verify the version selector dropdown navigates between them, and verify the root URL redirects to `/latest/`.

### Implementation for User Story 5

- [x] T028 [US5] Configure mike versioning provider in `mkdocs.yml` with Material theme `extra.version.provider: mike` and version selector integration (FR-034)
- [x] T029 [US5] Create `docs/changelog.md` "What's New" page for the current version (v0.1) summarizing initial SDK features, API surface, and capabilities (FR-035)
- [x] T030 [US5] Update `.github/workflows/docs.yml` to use `mike deploy --push --update-aliases <version> latest` for release tags and `mike deploy --push dev` for main branch pushes (FR-034)

**Checkpoint**: Version selector appears in site header. Multiple versions coexist at `/0.1/`, `/latest/`, `/dev/` URL paths.

---

## Phase 8: User Story 6 — Notebook Examples Gallery (Priority: P6)

**Goal**: Deliver an examples gallery with rendered Python scripts (syntax-highlighted) and Jupyter notebooks. Each example has a download link. Adding a new file to `examples/` auto-includes it in the gallery.

**Independent Test**: Build docs, navigate to Examples section, verify all 6 Python scripts render as syntax-highlighted pages and the MNIST notebook renders with code cells and outputs. Verify download links work.

### Implementation for User Story 6

- [x] T031 [US6] Create `docs/examples/index.md` gallery page listing all example scripts and notebooks with titles and one-line descriptions (FR-026)
- [x] T032 [P] [US6] Create `docs/examples/cluster-basics.md` wrapper page for `examples/cluster_basics.py` using pymdownx.snippets to include source, with description and download link (FR-028, FR-029)
- [x] T033 [P] [US6] Create `docs/examples/job-submission.md` wrapper page for `examples/job_submission.py` using pymdownx.snippets to include source, with description and download link (FR-028, FR-029)
- [x] T034 [P] [US6] Create `docs/examples/advanced-config.md` wrapper page for `examples/advanced_config.py` using pymdownx.snippets to include source, with description and download link (FR-028, FR-029)
- [x] T035 [P] [US6] Create `docs/examples/async-client.md` wrapper page for `examples/async_client.py` using pymdownx.snippets to include source, with description and download link (FR-028, FR-029)
- [x] T036 [P] [US6] Create `docs/examples/ray-serve-deployment.md` wrapper page for `examples/ray_serve_deployment.py` using pymdownx.snippets to include source, with description and download link (FR-028, FR-029)
- [x] T037 [P] [US6] Create `docs/examples/openshift-features.md` wrapper page for `examples/openshift_features.py` using pymdownx.snippets to include source, with description and download link (FR-028, FR-029)
- [x] T038 [US6] Configure mkdocs-jupyter in `mkdocs.yml` nav to render `examples/mnist_training.ipynb` directly as a page with `include_source: true` for download link and `execute: false` (FR-027, FR-029)

**Checkpoint**: Examples gallery shows 6 script pages + 1 notebook page. All have syntax highlighting and download links. Adding a new notebook auto-includes it (SC-007).

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, cross-story integration checks, and quickstart scenario verification

- [x] T039 Run `mkdocs build --strict` end-to-end and fix all warnings and errors across all sections
- [x] T040 Validate all 6 quickstart.md scenarios: local preview (Scenario 1), API reference auto-gen (Scenario 2), new notebook addition (Scenario 3), broken link detection (Scenario 4), version deployment (Scenario 5), CI build (Scenario 6)
- [x] T041 Verify search returns relevant results for key SDK terms: "cluster", "job logs", "storage volume", "RuntimeEnv", "OpenShift", "AsyncKubeRayClient", "ClusterHandle", "SDKConfig" (SC-005)
- [x] T042 Verify every guide page contains at least one runnable code example with Python syntax highlighting (FR-036, FR-037)
- [x] T043 Verify all cross-links between guide pages and API reference pages resolve correctly — zero broken links (SC-004)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational. No dependency on other stories.
- **US2 (Phase 4)**: Depends on Foundational (gen_ref_pages.py created in T006). No dependency on US1 content but cross-links from US1 pages to API reference improve with US2 complete.
- **US3 (Phase 5)**: Depends on Foundational. No dependency on other stories.
- **US4 (Phase 6)**: Depends on at least one user story being complete (needs content to validate pipeline).
- **US5 (Phase 7)**: Depends on US4 (CI pipeline exists for automated deployment).
- **US6 (Phase 8)**: Depends on Foundational. No dependency on other stories.
- **Polish (Phase 9)**: Depends on all user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — standalone, delivers the MVP
- **US2 (P2)**: Can start after Foundational — standalone but cross-links improve with US1
- **US3 (P3)**: Can start after Foundational — fully independent from US1/US2
- **US4 (P4)**: Requires at least US1 or US2 complete — needs content to validate
- **US5 (P5)**: Requires US4 — needs CI pipeline for deployment
- **US6 (P6)**: Can start after Foundational — fully independent from US1/US2/US3

### Within Each User Story

- All guide pages within US1 are independent and marked [P] (parallel)
- All developer guide pages within US3 are independent and marked [P] (parallel)
- All example wrapper pages within US6 are independent and marked [P] (parallel)
- US2 tasks are sequential: configure → generate → validate
- US4 tasks are sequential: create pipeline → validate it
- US5 tasks are sequential: configure → create changelog → update pipeline

### Parallel Opportunities

- **Phase 2**: T004 and T005 can run in parallel (different files)
- **Phase 3 (US1)**: All 11 guide pages (T007–T017) can run in parallel
- **Phase 5 (US3)**: All 5 developer guide pages (T021–T025) can run in parallel
- **Phase 8 (US6)**: All 6 example wrapper pages (T032–T037) can run in parallel
- **Cross-story**: US1, US2, US3, and US6 can all start in parallel after Foundational completes

---

## Parallel Example: User Story 1

```bash
# Launch all User Guide pages in parallel (all different files, no dependencies):
Task: "Create docs/user-guide/getting-started/installation.md" (T007)
Task: "Create docs/user-guide/getting-started/quick-start.md" (T008)
Task: "Create docs/user-guide/cluster-management.md" (T009)
Task: "Create docs/user-guide/job-submission.md" (T010)
Task: "Create docs/user-guide/ray-serve.md" (T011)
Task: "Create docs/user-guide/storage-runtime-env.md" (T012)
Task: "Create docs/user-guide/openshift.md" (T013)
Task: "Create docs/user-guide/experiment-tracking.md" (T014)
Task: "Create docs/user-guide/async-usage.md" (T015)
Task: "Create docs/user-guide/error-handling.md" (T016)
Task: "Create docs/user-guide/configuration.md" (T017)
```

## Parallel Example: User Story 6

```bash
# Launch all example wrapper pages in parallel:
Task: "Create docs/examples/cluster-basics.md" (T032)
Task: "Create docs/examples/job-submission.md" (T033)
Task: "Create docs/examples/advanced-config.md" (T034)
Task: "Create docs/examples/async-client.md" (T035)
Task: "Create docs/examples/ray-serve-deployment.md" (T036)
Task: "Create docs/examples/openshift-features.md" (T037)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T006)
3. Complete Phase 3: User Story 1 (T007–T017)
4. **STOP and VALIDATE**: Run `mkdocs build --strict`, verify User Guide renders correctly
5. Users can browse getting-started guides and all feature guides

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 (User Guide) → Test independently → **MVP delivered**
3. Add US2 (API Reference) → Cross-links from guides now resolve → Richer experience
4. Add US3 (Developer Guide) → Contributors can onboard
5. Add US4 (CI Pipeline) → Automated validation and deployment
6. Add US5 (Versioning) → Version selector dropdown live
7. Add US6 (Examples Gallery) → Notebooks and scripts browsable
8. Polish → Final validation, search coverage, quickstart scenarios

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (User Guide — 11 pages)
   - Developer B: US2 (API Reference — 3 tasks) then US4 (CI Pipeline — 2 tasks)
   - Developer C: US3 (Developer Guide — 5 pages) then US6 (Examples — 8 tasks)
3. After US4 complete: Developer B tackles US5 (Versioning)
4. All stories integrate independently via mkdocs.yml nav

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable via `mkdocs build --strict`
- No test tasks generated — `mkdocs build --strict` serves as the validation suite
- API reference generation uses static analysis (griffe) — no SDK runtime dependencies needed during build
- Guide pages are hand-authored markdown with code examples — "automated" refers to the build pipeline
- Commit after each task or logical group
- Stop at any checkpoint to validate the story independently
