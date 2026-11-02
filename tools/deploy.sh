#!/usr/bin/env bash
# Deployment ledger (deployments.jsonl): record / verify / list.
# Thin wrapper around tools/deploy.py; see README.md "Deployment ledger".
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "${REPO_ROOT}/tools/deploy.py" --repo-root "${REPO_ROOT}" "$@"
