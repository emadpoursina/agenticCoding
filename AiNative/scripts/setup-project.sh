#!/usr/bin/env bash
# Install or repair AiNative agents/rules in one app repo (new or existing).
# Safe to re-run. Does not overwrite an existing .cursor/rules/ai-rules.mdc.
# Home is this checkout; broken $AINATIVE_HOME is ignored if this tree is valid.
#
#   ./scripts/setup-project.sh ~/projects/app
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec node "$SCRIPT_DIR/ainative-link.mjs" project "$@"
