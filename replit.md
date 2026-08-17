# Replit Multi-Agent Orchestrator

RMAO is a Python backend that plans project work, executes independent tasks
through bounded workers, and publishes successful artifacts through mock or
GitHub branch/pull-request workflows.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `cd replica-pro && python -m rmao.cli.main serve --host 0.0.0.0 --port 8000` — run the RMAO HTTP API
- `cd replica-pro && rmao plan "Build a project" --tasks 3` — create a plan
- `cd replica-pro && rmao run "Build a project" --tasks 3` — run mock orchestration
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env for the existing API server: `DATABASE_URL` — Postgres connection string
- RMAO configuration: see `replica-pro/.env.example`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `replica-pro/src/rmao/config/` — typed environment configuration and startup validation
- `replica-pro/src/rmao/planner/` — LLM-backed task planning and safety validation
- `replica-pro/src/rmao/pool/` and `executor/` — worker leasing and dependency-aware parallel execution
- `replica-pro/src/rmao/execution/` — mock execution and explicit Replit-provider boundary
- `replica-pro/src/rmao/github/` — mock and GitHub REST branch/PR workflow
- `replica-pro/src/rmao/orchestration/` — dependency-injected composition root
- `replica-pro/src/rmao/api/` and `cli/` — HTTP and command-line entry points
- `replica-pro/tests/` — RMAO unit and integration coverage

## Architecture decisions

- Mock mode is deterministic and never runs arbitrary commands or accesses the network.
- The Replit execution provider fails explicitly until an official execution API is available.
- GitHub publishing is provider-neutral; real mode uses the GitHub REST API and mock mode stays in memory.
- HTTP handling uses the standard library to keep the standalone Python backend lightweight.

## Product

RMAO supports planning, dry-run inspection, bounded parallel task execution,
progress events, cancellation requests, safe mock artifacts, and optional
GitHub pull-request publication.

## User preferences

- Keep the orchestrator isolated under `replica-pro`; do not overwrite unrelated workspace artifacts.

## Gotchas

- Use `RMAO_MODE=mock` for local runs without credentials.
- Real mode requires the provider-specific LLM secret plus `GITHUB_TOKEN`,
  `GITHUB_OWNER`, and `GITHUB_REPOSITORY`.
- The standalone Python service is not automatically the existing Node API
  workflow; start it with the RMAO CLI command when needed.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
