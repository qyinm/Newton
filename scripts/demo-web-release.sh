#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
WORKSPACE="qa/dogfood/login"
WORKSPACE_ABS="$ROOT/$WORKSPACE"
SCENARIO_DIR="$WORKSPACE/scenario"
RUNS_DIR="$WORKSPACE/runs"
APP_PORT="$("$PYTHON_BIN" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
DENIED_PORT="$("$PYTHON_BIN" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
APP_BASE_URL="http://127.0.0.1:$APP_PORT"
DENIED_BASE_URL="http://127.0.0.1:$DENIED_PORT"

if [ -n "${NEWTON_CMD:-}" ]; then
  NEWTON=($NEWTON_CMD)
else
  NEWTON=(uv run --extra dev --extra web newton)
fi

run_newton() {
  "${NEWTON[@]}" "$@"
}

start_server() {
  local port="$1"
  local directory="$2"
  "$PYTHON_BIN" -m http.server "$port" --bind 127.0.0.1 --directory "$directory" >/tmp/newton-demo-"$port".log 2>&1 &
  echo "$!"
}

wait_for_url() {
  local url="$1"
  "$PYTHON_BIN" - "$url" <<'PY'
import sys
import time
from urllib.request import urlopen

url = sys.argv[1]
deadline = time.time() + 10
last_error = None
while time.time() < deadline:
    try:
        with urlopen(url, timeout=1) as response:
            if response.status < 500:
                raise SystemExit(0)
    except Exception as exc:  # noqa: BLE001
        last_error = exc
        time.sleep(0.2)
raise SystemExit(f"server did not become ready at {url}: {last_error}")
PY
}

latest_run_for_status() {
  local status="$1"
  "$PYTHON_BIN" - "$RUNS_DIR/index.jsonl" "$status" <<'PY'
import json
import sys
from pathlib import Path

index_path = Path(sys.argv[1])
status = sys.argv[2]
entries = [json.loads(line) for line in index_path.read_text().splitlines() if line.strip()]
for entry in reversed(entries):
    if entry.get("status") == status:
        print(Path(entry["result_path"]).parent)
        raise SystemExit(0)
raise SystemExit(f"no {status} run found in {index_path}")
PY
}

APP_PID="$(start_server "$APP_PORT" "$WORKSPACE_ABS/web/passing")"
DENIED_PID="$(start_server "$DENIED_PORT" "$WORKSPACE_ABS/web/failing")"
cleanup() {
  kill "$APP_PID" "$DENIED_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

wait_for_url "$APP_BASE_URL/login.html"
wait_for_url "$DENIED_BASE_URL/login.html"

mkdir -p "$RUNS_DIR"
find "$RUNS_DIR" -maxdepth 1 -type d -name 'run_*' -exec rm -rf {} +
rm -f "$RUNS_DIR/index.jsonl" "$SCENARIO_DIR/login_ticket.template.plan.json"

run_newton qa plan-bundle "$WORKSPACE/inputs/ticket.md" \
  --source "$WORKSPACE/inputs/policy.md" \
  --source "$WORKSPACE/inputs/design-notes.md" \
  --out "$WORKSPACE" \
  --bundle-dir-name plan
run_newton qa bundle-validate "$WORKSPACE/plan"
run_newton qa bundle-review "$WORKSPACE/plan" --agent template

run_newton qa plan "$WORKSPACE/inputs/ticket.md" \
  --agent template \
  --target web \
  --base-url http://127.0.0.1:8000 \
  --out "$SCENARIO_DIR"

run_newton qa validate "$SCENARIO_DIR/login-smoke.generated.yaml"
run_newton qa validate "$SCENARIO_DIR/login-validation.generated.yaml"
run_newton qa validate "$SCENARIO_DIR/login-permission.generated.yaml"

PLAN_PROVENANCE="$SCENARIO_DIR/ticket.template.plan.json"

run_newton qa run "$SCENARIO_DIR/login-smoke.generated.yaml" \
  --target web \
  --backend playwright \
  --base-url "$APP_BASE_URL" \
  --plan-provenance "$PLAN_PROVENANCE" \
  --out "$RUNS_DIR"
run_newton qa run "$SCENARIO_DIR/login-validation.generated.yaml" \
  --target web \
  --backend playwright \
  --base-url "$APP_BASE_URL" \
  --out "$RUNS_DIR"
run_newton qa run "$SCENARIO_DIR/login-permission.generated.yaml" \
  --target web \
  --backend playwright \
  --base-url "$APP_BASE_URL" \
  --out "$RUNS_DIR"
run_newton qa run "$SCENARIO_DIR/login-smoke.generated.yaml" \
  --target web \
  --backend playwright \
  --base-url "$DENIED_BASE_URL" \
  --plan-provenance "$PLAN_PROVENANCE" \
  --allow-failure \
  --out "$RUNS_DIR"

PASSED_RUN="$(latest_run_for_status passed)"
FAILED_RUN="$(latest_run_for_status failed)"

run_newton qa tracker-update-from-run "$WORKSPACE/plan/qa-run-tracker.md" \
  --item 5 \
  --env stg \
  --run "$FAILED_RUN"
run_newton qa bug-draft "$WORKSPACE/plan/qa-run-tracker.md" \
  --out "$WORKSPACE/bug-ticket-draft.md"
run_newton qa handoff "$WORKSPACE" --out "$WORKSPACE/agent-handoff.md"

echo "bundle: $WORKSPACE/plan"
echo "scenarios: $SCENARIO_DIR"
echo "passed_run: $PASSED_RUN"
echo "failed_run: $FAILED_RUN"
echo "failed_report: $FAILED_RUN/qa-report.md"
echo "handoff: $WORKSPACE/agent-handoff.md"
