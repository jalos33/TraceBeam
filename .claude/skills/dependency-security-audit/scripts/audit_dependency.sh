#!/usr/bin/env bash
# Audit a single package (or the whole requirements.txt) for known CVEs.
# Usage:
#   audit_dependency.sh pip <package>[==version]
#   audit_dependency.sh pip all            # audits requirements.txt in CWD
#   audit_dependency.sh npm <package>[@version]
set -euo pipefail

ecosystem="${1:?ecosystem required: pip|npm}"
target="${2:?package name required, or 'all'}"

case "$ecosystem" in
  pip)
    command -v pip-audit >/dev/null 2>&1 || pip install --quiet pip-audit
    if [ "$target" = "all" ]; then
      if [ ! -f requirements.txt ]; then
        echo "No requirements.txt in $(pwd)" >&2
        exit 1
      fi
      pip-audit -r requirements.txt
    else
      tmpdir="$(mktemp -d)"
      trap 'rm -rf "$tmpdir"' EXIT
      python3 -m venv "$tmpdir/venv"
      # shellcheck disable=SC1091
      source "$tmpdir/venv/bin/activate"
      pip install --quiet "$target"
      pip-audit
      deactivate
    fi
    ;;
  npm)
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "$tmpdir"' EXIT
    (cd "$tmpdir" && npm init -y --silent >/dev/null && npm install --silent "$target" && npm audit)
    ;;
  *)
    echo "Unknown ecosystem: $ecosystem (expected pip or npm)" >&2
    exit 1
    ;;
esac
