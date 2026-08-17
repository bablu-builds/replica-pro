---
name: GitHub PAT Git authentication
description: Secure GitHub push behavior for fine-grained personal access tokens in this workspace.
---

For Git transport, authenticate a GitHub PAT with HTTP Basic auth using the `x-access-token` username; an API-valid token sent as a Bearer or token header can still be rejected by `git push`.

**Why:** GitHub accepted the token through its API but rejected Git transport until the standard Basic auth form was used.

**How to apply:** Keep the token in Replit Secrets, build the Basic auth header at command runtime, and use `--force-with-lease` only after confirming the remote tip when replacing a branch.