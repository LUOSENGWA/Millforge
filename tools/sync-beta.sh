#!/usr/bin/env bash
# Sync beta module artifacts from the fork's GitHub releases into releases/.
# Thin wrapper around tools/sync_beta.py; see releases/README.md.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "${REPO_ROOT}/tools/sync_beta.py" --repo-root "${REPO_ROOT}" "$@"
