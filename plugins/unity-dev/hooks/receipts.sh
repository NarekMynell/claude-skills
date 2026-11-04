#!/usr/bin/env bash
# unity-dev PreToolUse hook on Write and Edit: receipts in docs/proofs/ are written by the checks, so editing one by hand is
# refused. docs/proofs/not-applicable.txt is the exception: it is where a person or Claude says why a check doesn't apply.
# Costs one comparison on any other file. Always exits 0.

input="$(cat)"
case "$input" in
  *docs/proofs/not-applicable.txt*) exit 0 ;;
  *docs/proofs/*) ;;
  *) exit 0 ;;
esac

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
. "$root/hooks/common.sh"
[ "$(standards_state "$(working_folder "$(hook_cwd "$input")")")" = on ] || exit 0

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Receipts in docs/proofs/ are written by the checks that ran. Run the check. If it does not apply to this project, add a line to docs/proofs/not-applicable.txt: family: reason."}}\n'
exit 0
