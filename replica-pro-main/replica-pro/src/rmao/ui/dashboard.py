"""Streamlit monitoring dashboard for a running RMAO API service.

Run with:

    streamlit run src/rmao/ui/dashboard.py
"""

from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import streamlit as st
from dotenv import load_dotenv


load_dotenv()
API_URL = os.getenv("RMAO_API_URL", "http://127.0.0.1:8000").rstrip("/")
LOG_PATH = Path(os.getenv("RMAO_LOG_FILE", "rmao.log"))


def main() -> None:
    st.set_page_config(page_title="Replica-Pro Monitor", page_icon="R")
    if not _authenticated():
        return

    st.title("Replica-Pro Monitor")
    st.caption(f"API: {API_URL}")
    if st.button("Refresh"):
        st.rerun()

    runs = _api_json("/v1/runs")
    if isinstance(runs, dict) and "error" in runs:
        st.error(runs["error"].get("message", "Unable to load runs"))
    else:
        _render_runs(runs if isinstance(runs, list) else [])

    st.divider()
    _render_logs()
    st.divider()
    _render_trigger_form()


def _authenticated() -> bool:
    expected_user = os.getenv("RMAO_DASHBOARD_USERNAME", "").strip()
    expected_password = os.getenv("RMAO_DASHBOARD_PASSWORD", "")
    if not expected_user or not expected_password:
        st.error("Dashboard authentication is not configured.")
        st.caption("Set RMAO_DASHBOARD_USERNAME and RMAO_DASHBOARD_PASSWORD in .env.")
        return False
    if st.session_state.get("rmao_authenticated"):
        return True

    with st.form("dashboard_login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
    if submitted and hmac.compare_digest(username, expected_user) and hmac.compare_digest(
        password, expected_password
    ):
        st.session_state["rmao_authenticated"] = True
        st.rerun()
    elif submitted:
        st.error("Invalid username or password")
    return False


def _render_runs(runs: list[dict[str, Any]]) -> None:
    st.subheader("Runs")
    if not runs:
        st.info("No orchestrator runs yet.")
        return
    for run in runs:
        run_id = str(run.get("run_id", "unknown"))
        state = str(run.get("state", "unknown")).split(".")[-1]
        with st.expander(f"{run_id} — {state}", expanded=state in {"planning", "executing"}):
            st.write(f"Status: **{state}**")
            st.write(f"Duration: {float(run.get('duration_seconds', 0)):.2f}s")
            task_results = run.get("task_results", {})
            if isinstance(task_results, dict):
                st.write(
                    {
                        task_id: str(result.get("success", False)) if isinstance(result, dict) else result
                        for task_id, result in task_results.items()
                    }
                )
            links = run.get("pr_links", [])
            if isinstance(links, list):
                for link in links:
                    if isinstance(link, str) and link:
                        st.markdown(f"[Open GitHub pull request]({link})")
            if run.get("repo_url"):
                st.markdown(f"[Open repository]({run['repo_url']})")


def _render_logs() -> None:
    st.subheader("Recent logs")
    lines = _tail_lines(LOG_PATH, 100)
    if not lines:
        st.info(f"No log file found at {LOG_PATH}.")
        return
    st.code("\n".join(lines), language="json")


def _render_trigger_form() -> None:
    st.subheader("Start a build")
    with st.form("new_build"):
        request = st.text_area("Project request", placeholder="Build a notes app")
        tasks = st.number_input("Tasks", min_value=1, max_value=16, value=4, step=1)
        submitted = st.form_submit_button("Run orchestrator")
    if submitted:
        if not request.strip():
            st.error("Enter a project request.")
            return
        result = _api_json(
            "/v1/runs",
            method="POST",
            payload={"request": request.strip(), "tasks": int(tasks)},
        )
        if isinstance(result, dict) and result.get("run_id"):
            st.success(f"Run started: {result['run_id']}")
        else:
            st.error(_error_message(result))


def _api_json(
    path: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{API_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body else {},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        return {"error": {"message": str(error)}}


def _tail_lines(path: Path, limit: int) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except OSError:
        return []


def _error_message(value: Any) -> str:
    if isinstance(value, dict):
        error = value.get("error")
        if isinstance(error, dict):
            return str(error.get("message", "Request failed"))
    return "Request failed"


if __name__ == "__main__":
    main()