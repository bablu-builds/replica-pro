---
name: Nested Python package installation
description: Workspace-safe dependency installation for Python projects nested inside the pnpm monorepo
---

When installing dependencies for a nested Python project, the package installer
may bootstrap `main.py`, `pyproject.toml`, and `uv.lock` at the workspace root
instead of the Python project directory.

**Why:** The workspace is primarily a pnpm monorepo, but Python package tooling
can infer the current directory as a new uv project when the nested package is
not installed editable.

**How to apply:** Use the package-management flow for dependencies, then check
the workspace root and remove only newly generated uv helper files that are not
part of the target Python project.