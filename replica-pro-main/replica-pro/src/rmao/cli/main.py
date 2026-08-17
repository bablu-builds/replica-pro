"""Command-line entry point for planning, execution, and HTTP serving."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from ..config import load_config, validate_config
from ..api.server import serve
from ..logging.redaction import setup_logging
from ..orchestration.orchestrator import build_orchestrator


def _config():
    config = load_config()
    validate_config(config)
    setup_logging(config.log_level, config.log_redact_secrets)
    return config


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in {"plan", "run", "serve", "validate-config", "-h", "--help"}:
        argv.insert(0, "plan")
    parser = argparse.ArgumentParser(
        prog="rmao",
        description="Replit Multi-Agent Orchestrator",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)
    for command in ("plan", "run"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("request", help="Project request")
        command_parser.add_argument("--tasks", type=int, default=4)
        if command == "run":
            command_parser.add_argument(
                "--dry-run",
                action="store_true",
                help="Plan only; do not execute or publish",
            )
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    subparsers.add_parser("validate-config")
    args = parser.parse_args(argv)
    if args.command == "validate-config":
        _config()
        print("Configuration is valid.")
        return
    if args.command == "serve":
        serve(_config(), args.host, args.port)
        return
    if args.command not in {"plan", "run"}:
        parser.print_help()
        return
    if not 1 <= args.tasks <= 16:
        parser.error("--tasks must be between 1 and 16")
    config = _config()
    if args.command == "run" and args.dry_run:
        config.mode = "dry_run"
    if args.tasks > config.max_tasks:
        parser.error(f"--tasks cannot exceed configured RMAO_MAX_TASKS ({config.max_tasks})")
    orchestrator = build_orchestrator(config, args.tasks)
    if args.command == "plan":
        result = asyncio.run(orchestrator.plan(args.request, args.tasks))
    else:
        result = asyncio.run(orchestrator.run(args.request, args.tasks))
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()