---
name: Standalone project runs
description: Durable guidance for running uploaded projects that are not web artifacts.
---

When an uploaded project is a standalone package rather than a web app, verify its declared entry point and run it directly in its supported mock or local mode before trying to attach it to a preview workflow.

**Why:** Standalone packages do not automatically get a Replit preview workflow, and an archive can contain an incomplete or malformed entry point that prevents a meaningful preview.

**How to apply:** Inspect the package manifest, compile the source, and use the project's own command-line or local entry point. Only add a web wrapper if the user explicitly asks for a browser-based app.