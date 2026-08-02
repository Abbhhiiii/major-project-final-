#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="$project_root/.venv/bin/python"

if [[ ! -x "$python_bin" ]]; then
  echo "Missing .venv. Create it and install the project first." >&2
  exit 1
fi

if command -v npm >/dev/null 2>&1; then
  npm_bin="$(command -v npm)"
elif [[ -x /tmp/codex-node-24.15.0/bin/npm ]]; then
  npm_bin="/tmp/codex-node-24.15.0/bin/npm"
  export PATH="/tmp/codex-node-24.15.0/bin:$PATH"
else
  echo "npm is required to run the dashboard." >&2
  exit 1
fi

cd "$project_root"
"$python_bin" -m uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000 &
backend_pid=$!
(
  cd "$project_root/apps/dashboard"
  "$npm_bin" run dev -- --host 127.0.0.1
) &
dashboard_pid=$!

cleanup() {
  kill "$backend_pid" "$dashboard_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Backend:  http://127.0.0.1:8000"
echo "Dashboard: http://127.0.0.1:5173"
wait
