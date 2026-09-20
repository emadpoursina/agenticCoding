#!/usr/bin/env bash
# Install or repair global Cursor slash commands + alert hook (~/.cursor).
# Safe to re-run. Does not touch any project repo.
# Home is this checkout; broken $AINATIVE_HOME is ignored if this tree is valid.
#
#   ./scripts/setup-machine.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec node "$SCRIPT_DIR/ainative-link.mjs" machine "$@"
