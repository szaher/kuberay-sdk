"""Generate API reference pages for mkdocstrings.

This script walks the kuberay_sdk package and generates a virtual markdown
page for each module. Each page contains a `:::` directive that mkdocstrings
resolves into rendered API documentation at build time.

It also generates a SUMMARY.md file that mkdocs-literate-nav uses to build
the API Reference navigation tree.
"""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()
mod_symbol = '<code class="doc-symbol doc-symbol-nav doc-symbol-module"></code>'

src = Path("src")

for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = tuple(module_path.parts)

    # Skip private modules and __pycache__
    if any(part.startswith("_") and part != "__init__" for part in parts):
        continue
    if "__pycache__" in parts:
        continue

    # Handle __init__.py — use the parent directory as the page
    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
        if not parts:
            continue

    nav_parts = [f"{mod_symbol} {part}" for part in parts]
    nav[nav_parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"::: {ident}\n")

    mkdocs_gen_files.set_edit_path(full_doc_path, path.relative_to(src))

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
