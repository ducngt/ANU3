#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$ROOT" ]; then
  echo "ERROR: run this from inside the ANU3 Codespace repository." >&2
  exit 2
fi
cd "$ROOT"

BRANCH="$(git branch --show-current)"
if [ "$BRANCH" != "main" ]; then
  echo "ERROR: expected branch main, found: $BRANCH" >&2
  exit 3
fi

if [ ! -f .github/workflows/phase1-verify.yml ] || [ ! -f anu-phase1-kernel/pyproject.toml ]; then
  echo "ERROR: CI activation package is not extracted at the repository root." >&2
  exit 4
fi

git add .github/workflows/phase1-verify.yml anu-phase1-kernel HUMAN-PUBLISH-ONLY.txt HUMAN-PUBLISH.sh

if git diff --cached --quiet; then
  echo "No new ANU Phase 1 CI activation changes to publish."
else
  git commit -m "Activate ANU Phase 1 PostgreSQL CI verification"
fi

git push origin main

echo "PUBLISHED: GitHub Actions should start ANU Phase 1 Verification automatically."
