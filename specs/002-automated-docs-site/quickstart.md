# Quickstart: Automated Documentation Site

**Feature**: 002-automated-docs-site
**Date**: 2026-02-23

## Scenario 1: Build and Preview Docs Locally

A contributor wants to preview the documentation site while editing guide pages.

```bash
# Install documentation dependencies
pip install -e ".[docs]"

# Start the local dev server with hot reload
mkdocs serve
# Open http://127.0.0.1:8000 in a browser
# Edit any markdown file in docs/ — the browser auto-refreshes
```

**Expected result**: The site renders in the browser with all sections (User Guide, Developer Guide, API Reference, Examples) navigable. Editing a markdown file triggers an immediate rebuild and browser refresh.

## Scenario 2: Verify API Reference Auto-Generation

A contributor wants to confirm that a docstring change appears in the API reference.

```bash
# 1. Edit a docstring in the source code
#    e.g., change the docstring of KubeRayClient.create_cluster in src/kuberay_sdk/client.py

# 2. Build the docs
mkdocs build --strict

# 3. Open the generated API reference page
open site/reference/kuberay_sdk/client/index.html
# The updated docstring should be visible with method signature, type annotations, and examples
```

**Expected result**: The API reference page for `KubeRayClient.create_cluster` shows the updated docstring, method signature with parameter types, return type `ClusterHandle`, and cross-links to related classes.

## Scenario 3: Add a New Example Notebook

A contributor adds a new Jupyter notebook example and wants it to appear in the gallery.

```bash
# 1. Place the notebook in examples/
cp my_new_example.ipynb examples/

# 2. Add it to the examples nav section in mkdocs.yml (or let auto-discovery handle it)

# 3. Build and verify
mkdocs build --strict
open site/examples/
# The new notebook should appear in the gallery with a rendered preview and download link
```

**Expected result**: The gallery page lists the new notebook with its title (from the first markdown heading) and the rendered cells are viewable on the page.

## Scenario 4: Detect Broken Links

A contributor introduces a broken cross-link in a guide page.

```bash
# 1. Add a broken link to a guide page
echo "[broken link](nonexistent-page.md)" >> docs/user-guide/cluster-management.md

# 2. Build in strict mode
mkdocs build --strict
# Expected: Build FAILS with an error identifying the broken link
```

**Expected result**: The build exits with code 1 and prints an error message identifying the broken link and its location (file and line).

## Scenario 5: Deploy a New Version

A maintainer releases version 0.2.0 and wants to deploy versioned docs.

```bash
# 1. Build and deploy the new version
mike deploy --push --update-aliases 0.2 latest

# 2. Set the default redirect
mike set-default --push latest

# 3. Verify locally
mike serve
# Open http://127.0.0.1:8000
# The version selector should show: 0.1, 0.2 (latest), dev
# Selecting 0.1 should show the old docs
# Selecting 0.2 should show the new docs
```

**Expected result**: Both versions are accessible at their respective URL paths. The version selector dropdown appears in the header. Visiting the root URL redirects to `/latest/`.

## Scenario 6: Full CI Build Validation

The CI pipeline runs on every PR to validate the documentation.

```bash
# 1. Install deps
pip install -e ".[docs]"

# 2. Build with strict mode
mkdocs build --strict

# 3. Expected: Exit code 0 if all pages build correctly,
#    all cross-links resolve, and no warnings are emitted
echo $?  # Should print 0
```

**Expected result**: The build completes in under 60 seconds. Exit code 0 means the docs are valid. Any broken links, missing pages, or docstring issues cause a non-zero exit code.
