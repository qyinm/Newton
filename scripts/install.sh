#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${NEWTON_REPO_URL:-https://github.com/qyinm/Newton.git}"
REF="${NEWTON_REF:-main}"
WITH_WEB=1
DRY_RUN="${NEWTON_INSTALL_DRY_RUN:-0}"

usage() {
  cat <<'USAGE'
Install the Newton QA CLI.

Usage:
  install.sh [--no-web] [--ref <git-ref>] [--repo <git-url>]

Options:
  --no-web       Install only the base CLI without Playwright dependencies.
  --ref REF      Git ref to install. Defaults to main.
  --repo URL     Git repository URL. Defaults to https://github.com/qyinm/Newton.git.
  -h, --help     Show this help.

Environment:
  NEWTON_INSTALL_DRY_RUN=1   Print commands without executing them.
  NEWTON_REPO_URL=URL        Override the repository URL.
  NEWTON_REF=REF             Override the git ref.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-web)
      WITH_WEB=0
      shift
      ;;
    --ref)
      REF="${2:?--ref requires a value}"
      shift 2
      ;;
    --repo)
      REPO_URL="${2:?--repo requires a value}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

run() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
  if [[ "$DRY_RUN" != "1" ]]; then
    "$@"
  fi
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command not found: $1" >&2
    return 1
  fi
}

PACKAGE_SPEC="git+${REPO_URL}@${REF}#egg=newton-qa"
if [[ "$WITH_WEB" == "1" ]]; then
  PACKAGE_SPEC="${PACKAGE_SPEC}[web]"
fi

if command -v uv >/dev/null 2>&1; then
  INSTALLER=(uv tool install --force "$PACKAGE_SPEC")
elif command -v pipx >/dev/null 2>&1; then
  INSTALLER=(pipx install --force "$PACKAGE_SPEC")
else
  echo "error: install requires uv or pipx." >&2
  echo "Install uv from https://docs.astral.sh/uv/ or install pipx, then rerun this script." >&2
  exit 1
fi

echo "Installing Newton QA CLI from ${REPO_URL}@${REF}"
run "${INSTALLER[@]}"

if [[ "$WITH_WEB" == "1" ]]; then
  if command -v uv >/dev/null 2>&1; then
    run uvx --from "$PACKAGE_SPEC" playwright install chromium
  else
    require_command python3
    echo "Installing Playwright Chromium with the active Python environment."
    echo "If this fails, run: python3 -m pip install 'newton-qa[web]' && python3 -m playwright install chromium" >&2
    run python3 -m playwright install chromium
  fi
fi

run newton version

cat <<'DONE'

Newton is installed.

Smoke it from any directory:
tmpdir=$(mktemp -d)
cat > "$tmpdir/login-ticket.md" <<'EOF'
# Login

Users should be able to log in with email and password.

Acceptance criteria:
- User can open login page
- User can enter email
- User can enter password
- User can submit
- User sees Dashboard
EOF
newton qa plan "$tmpdir/login-ticket.md" --agent template --target web --out "$tmpdir/scenarios"
newton qa validate "$tmpdir/scenarios/login-smoke.generated.yaml"
DONE
