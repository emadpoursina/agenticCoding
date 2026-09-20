#!/bin/bash
# Global Cursor hook: play an alert when the agent finishes or needs input.
#
# Modes (arg 1):
#   stop  - agent turn ended (job done or waiting for you)
#   ask   - agent invoked a tool that needs your answer (AskQuestion, SwitchMode)
#
# Env:
#   CURSOR_ALERT_SOUND  - path to .aiff/.wav (default: Glass.aiff)
#   CURSOR_ALERT_DISABLE=1 - master kill switch

set -u

mode="${1:-stop}"
[[ "${CURSOR_ALERT_DISABLE:-}" = "1" ]] && exit 0

input="$(cat 2>/dev/null || true)"
sound="${CURSOR_ALERT_SOUND:-/System/Library/Sounds/Glass.aiff}"

play_sound() {
  (
    if [[ -f "$sound" ]] && command -v afplay >/dev/null 2>&1; then
      afplay "$sound" >/dev/null 2>&1 || true
    elif command -v osascript >/dev/null 2>&1; then
      osascript -e 'beep 1' >/dev/null 2>&1 || true
    fi
  ) &
}

case "$mode" in
  stop)
    status="$(printf '%s' "$input" | jq -r '.status // empty' 2>/dev/null || true)"
    # Skip when the user explicitly stopped the run.
    [[ "$status" == "aborted" ]] && exit 0
    play_sound
    ;;
  ask)
    play_sound
    ;;
esac

# Observe-only: no stdout JSON so Cursor's approval flow is unchanged.
exit 0
