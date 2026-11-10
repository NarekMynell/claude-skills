#!/usr/bin/env bash
# core PreToolUse hook on Write and Edit: receipts in docs/proofs/ are written by the checks that ran, so editing one by hand is
# refused wherever a domain of this marketplace is on. docs/proofs/not-applicable.txt is the exception: it is where a person or
# Claude says why a check doesn't apply. Costs one comparison on any other file. Always exits 0.

input="$(cat)"
case "$input" in
  *docs/proofs/*) ;;
  *) exit 0 ;;
esac
# The file the tool writes, not its content: a CLAUDE.md that mentions docs/proofs/ is no receipt. The first "file_path".
path="$(printf '%s' "$input" | awk 'match($0, /"file_path"[[:space:]]*:[[:space:]]*"[^"]*"/) { print substr($0, RSTART, RLENGTH); exit }' | sed 's/^"file_path"[[:space:]]*:[[:space:]]*"//; s/"$//')"
case "$path" in
  */docs/proofs/not-applicable.txt | docs/proofs/not-applicable.txt) exit 0 ;;
  */docs/proofs/* | docs/proofs/*) ;;
  *) exit 0 ;;
esac

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
hooks_dir="$root/hooks"
[ -f "$hooks_dir/domains.txt" ] || exit 0
self=core
. "$hooks_dir/lib.sh"
load_domains
load_settings "$(working_folder "$(hook_cwd "$input")")"
any_switch && domain_loads "$base" || exit 0

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Receipts in docs/proofs/ are written by the checks that ran. Run the check. If it does not apply to this project, add a line to docs/proofs/not-applicable.txt: family: reason."}}\n'
exit 0
