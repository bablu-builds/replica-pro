# Replica-Pro

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-lightgrey?logo=github)](.github/workflows/ci.yml)

Replica-Pro is a multi-agent project orchestrator: it turns a project request
into validated, dependency-aware tasks, executes independent work in parallel,
and publishes successful artifacts through GitHub branches and pull requests.
It supports deterministic Mock Mode for local development and a Replit-backed
execution provider for configured automation sessions.

## Table of contents

- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Switching LLM providers](#switching-llm-providers)
- [Real mode](#real-mode)
- [HTTP API and dashboard](#http-api-and-dashboard)
- [Webhooks](#webhooks)
- [Docker](#docker)
- [Development](#development)
- [Detailed project documentation](#detailed-project-documentation)

## Prerequisites

- Python 3.9+; Python 3.11 is recommended for the current package metadata.
- Four optional Replit `connect.sid` values (`ACCOUNT1_SID` through
  `ACCOUNT4_SID`) when using the Replit execution provider.
- A GitHub token with permission to create branches and pull requests in the
  target repository when using real publishing.
- An API key for the selected LLM provider when not using Fake Mode.
- Git and, optionally, Docker Compose.

Keep credentials in Replit Secrets or a local `.env` file. Never commit `.env`.

## Quick start

```bash
cd replica-pro
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

The default setup is deterministic and needs no credentials:

```bash
RMAO_MODE=mock RMAO_LLM_PROVIDER=fake rmao run "Build a notes app" --tasks 3
```

Start the API service:

```bash
rmao serve --host 0.0.0.0 --port 8000
```

The health check is available at `GET /healthz`. The main JSON endpoints are
`POST /v1/plan`, `POST /v1/runs`, `GET /v1/runs`, `GET /v1/runs/{run_id}`, and
`POST /v1/runs/{run_id}/cancel`.

## Configuration

Copy `.env.example` to `.env` and set only the values required by the mode you
are using. Empty optional variables are ignored gracefully.

Important settings include:

| Variable | Purpose |
| --- | --- |
| `RMAO_MODE` | `mock`, `dry_run`, or `real` |
| `RMAO_LLM_PROVIDER` | `fake`, `openai`, `deepseek`, `kimi`, or `glm` |
| `RMAO_EXECUTION_PROVIDER` | `mock` or `replit` |
| `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPOSITORY` | Real GitHub publishing |
| `ACCOUNT1_SID` … `ACCOUNT4_SID` | Replit session rotation |
| `RMAO_WEBHOOK_TOKEN` | Inbound webhook authentication |
| `RMAO_DASHBOARD_USERNAME`, `RMAO_DASHBOARD_PASSWORD` | Dashboard login |

## Switching LLM providers

Choose a provider and its corresponding secret in `.env`:

```dotenv
RMAO_MODE=real
RMAO_LLM_PROVIDER=openai
OPENAI_API_KEY=...
```

The supported provider names are `openai`, `deepseek`, `kimi`, and `glm`.
Set the matching `DEEPSEEK_API_KEY`, `KIMI_API_KEY`, or `GLM_API_KEY` when
selecting those providers. `RMAO_LLM_BASE_URL` can override a compatible
endpoint.

## Real mode

1. Set `RMAO_MODE=real`.
2. Configure the selected LLM provider and API key.
3. Set `GITHUB_TOKEN`, `GITHUB_OWNER`, and `GITHUB_REPOSITORY`.
4. Set `GITHUB_CREATE_PULL_REQUESTS=true` and leave
   `GITHUB_MERGE_PULL_REQUESTS=false` until the workflow is trusted.
5. For Replit execution, set `RMAO_EXECUTION_PROVIDER=replit` and one or more
   `ACCOUNT*_SID` values.

The Replit provider uses Replit's internal GraphQL endpoint with the supplied
session cookies. That endpoint is not a public stable SDK surface, so keep the
provider isolated and expect operation shapes to require maintenance if Replit
changes its internal API. The provider retries transient failures, rotates
between configured sessions after authentication failures, and never prints
session values.

## HTTP API and dashboard

The FastAPI service returns standard JSON errors, emits JSON logs to stdout,
and limits `POST /v1/runs` and `POST /run` to 10 requests per minute per client.

Run the monitoring dashboard in a second terminal:

```bash
cd replica-pro
streamlit run src/rmao/ui/dashboard.py
```

Set `RMAO_DASHBOARD_USERNAME` and `RMAO_DASHBOARD_PASSWORD` before opening the
dashboard. It shows recent run states, task outcomes, pull-request links,
recent log lines, and a form for starting a build.

## Webhooks

Set `RMAO_WEBHOOK_TOKEN` and send a GitHub push payload to:

```text
POST /v1/webhooks/github
X-Orchestrator-Token: <configured token>
```

The request can use `project_query`, `request`, `rmao.request`, a
`.rmao/config.json` payload, or the first line of `head_commit.message`.
Valid requests receive HTTP 202 and a `run_id` while execution continues in
the background.

## Docker

From this repository root:

```bash
cp replica-pro/.env.example .env
docker compose up --build
```

The API listens on port 8000. The Redis service is included for deployments
that later need shared caching or rate-limit storage; the default rate limiter
is safe in-process for a single application instance.

## Development

```bash
cd replica-pro
python -m pytest
python -m compileall -q src
```

## Detailed project documentation

The package-level architecture and safe local setup are documented in
[`replica-pro/README.md`](replica-pro/README.md).