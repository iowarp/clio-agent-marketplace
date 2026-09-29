#!/usr/bin/env bash
# Isolated live clio-agent for OPAL tests (port 17990). Runs the rebased
# docs/chart-presentation-skill worktree (develop + table-query + chart guidance + clio-schemas 0.5.0).
L="D:/Libraries/Documents/projects/opal-work/live"
DATA="D:/Libraries/Documents/projects/OPAL/67_2026.04.09_OPAL.0002_Weston_PC/67_2026.04.09_OPAL.0002_Weston_PC"
VAR="D:/Libraries/Documents/projects/opal-work/variants"
export CLIO_USER_DIR="$L/user"
export CLIO_CODEX_VARIANT=sdk
export CLIO_DATA_DIR="$L/state/.clio_agent"
export CLIO_ALLOWED_ROOTS="$L/ws;$DATA;$VAR"
export CLIO_ARTIFACTS_ROOT="$L/ws/.clio/artifacts"
export CLIO_SHELL_MAX_COMMAND_CHARS=20000
export CLIO_SHELL_DEFAULT_OUTPUT_BYTES=65536
export CLIO_SHELL_MAX_OUTPUT_BYTES=524288
cd "D:/Libraries/Documents/projects/opal-work/clio-agent-chart-guidance"
.venv/Scripts/python.exe -m uvicorn clio_agent.gact.app:app --host 127.0.0.1 --port 17990
