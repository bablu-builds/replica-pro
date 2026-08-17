# Replit Multi-Agent Orchestrator

RMAO decomposes a project request into validated tasks, executes independent
tasks in parallel, and publishes successful artifacts through a safe
mockable GitHub branch and pull-request workflow.

## Architecture

```text
CLI / HTTP API
      |
Orchestrator composition root
  |       |          |
Planner  Executor   GitHub workflow
  |       |          |
 LLM   Agent pool  Mock or GitHub REST
          |
     Mock or Replit execution provider
```

The execution provider is deliberately pluggable. `mock` is deterministic and
does not run commands or access the network. The `replit` provider uses the
isolated async GraphQL adapter in `src/rmao/providers/replit.py`, rotates
configured sessions, retries transient failures, and fails explicitly when
sessions are missing or expired.

## Safe local setup

```bash
cd replica-pro
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

Mock mode is the default and needs no credentials:

```bash
RMAO_MODE=mock RMAO_LLM_PROVIDER=fake rmao run "Build a notes app" --tasks 3
```

Planning only:

```bash
rmao plan "Build a notes app" --tasks 3
```

Dry-run mode plans but does not execute or publish:

```bash
RMAO_MODE=dry_run RMAO_LLM_PROVIDER=fake rmao run "Build a notes app"
```

## HTTP API

Start the server:

```bash
rmao serve --host 0.0.0.0 --port 8000
```

The service is FastAPI-based and includes JSON error responses, JSON stdout
request logs, and a 10 requests/minute limit on run creation. Endpoints:

- `GET /healthz`
- `POST /v1/plan` with `{"request":"...", "tasks": 3}`
- `POST /v1/runs` with `{"request":"...", "tasks": 3}`
- `GET /v1/runs/<run_id>`
- `POST /v1/runs/<run_id>/cancel`
- `POST /v1/webhooks/github`

The API returns JSON errors and never logs request bodies or credentials.

## Real providers

For real planning, set the provider-specific LLM secret and choose
`RMAO_MODE=real`. For real GitHub publishing, configure `GITHUB_TOKEN`,
`GITHUB_OWNER`, and `GITHUB_REPOSITORY`. The GitHub provider creates one
`rmao/<run>/<task>` branch per successful task, writes validated artifacts,
opens pull requests, and only merges when `GITHUB_MERGE_PULL_REQUESTS=true`.

For Replit execution, set `RMAO_EXECUTION_PROVIDER=replit` and one or more
`ACCOUNT1_SID` through `ACCOUNT4_SID` values. Secrets belong in Replit Secrets
or the local `.env` file. Never commit them, put them in prompts, or include
them in logs. Real mode fails at startup when required configuration is absent.

## Verification

```bash
python -m pytest
python -m compileall -q src
```

The tests cover configuration validation, secret redaction, dependency cycles,
worker leasing, mock execution, parallel orchestration, GitHub mock publishing,
and the HTTP service layer.

## Limits

- Replit's internal GraphQL endpoint is not an official stable SDK surface and
  may need maintenance when Replit changes its internal API.
- GitHub REST publishing requires a repository with permission to create
  branches and pull requests.
- Mock artifacts are explicit test output, not production code generation.