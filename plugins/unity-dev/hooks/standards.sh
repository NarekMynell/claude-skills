#!/usr/bin/env bash
# unity-dev SessionStart and SubagentStart hook: loads the standards in a project that turned them on,
# with UNITY_DEV_STANDARDS=on under "env" in its Claude Code settings. Prints nothing otherwise.
# The hook output's cap is 10,000 characters, past which Claude gets only a preview, so the report is cut to fit.
# The standards are skills/standards/SKILL.md up to its "## When the user types the command"
# heading, with ${CLAUDE_SKILL_DIR} resolved. A new session also gets the toolchain check's findings.
# A subagent gets the standards too, because it knows only its brief, unless it only reads.

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
. "$root/hooks/common.sh"

input="$(cat)"
cwd="$(working_folder "$(hook_cwd "$input")")"
[ "$(standards_state "$cwd")" = on ] || exit 0

skill_dir="$root/skills/standards"
[ -f "$skill_dir/SKILL.md" ] || exit 0

standards="$(awk '
  NR == 1 && $0 == "---" { front = 1; next }
  front { if ($0 == "---") front = 0; next }
  /^## When the user types the command/ { exit }
  { print }
' "$skill_dir/SKILL.md")"
standards=${standards//'${CLAUDE_SKILL_DIR}'/"$skill_dir"}

event=SessionStart
message='"systemMessage":"unity-dev standards loaded",'
context="The user turned on the unity-dev standards for every session in this project, so they are loaded here as if the user had typed \`/unity-dev:standards\`.

$standards"

case "$input" in
  *'"SubagentStart"'*)
    case "$input" in
      *'"agent_type":"Explore"'* | *'"agent_type": "Explore"'* | *'"agent_type":"claude-code-guide"'* | *'"agent_type": "claude-code-guide"'* | *'"agent_type":"statusline-setup"'* | *'"agent_type": "statusline-setup"'*) exit 0 ;;
    esac
    event=SubagentStart
    message=''
    context="You are a subagent in a project with the unity-dev standards on: they bind your work as they bind the main session's. Before working, read the guides in the table below that match your task, with the Read tool.

$standards"
    ;;
esac

case "$input" in
  *'"source":"startup"'* | *'"source": "startup"'*)
    # The check can wait on the network. A watchdog stops it after 15 seconds, well inside the hook's
    # 30-second timeout, so a slow network costs the toolchain report, never the standards.
    report_file="$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/unity-dev-check.$$")"
    bash "$root/skills/toolchain/scripts/check.sh" "${CLAUDE_PROJECT_DIR:-$cwd}" "$CLAUDE_PLUGIN_DATA" \
      > "$report_file" 2>/dev/null < /dev/null &
    check_pid=$!
    ( sleep 15; kill "$check_pid" 2>/dev/null ) > /dev/null 2>&1 < /dev/null &
    watchdog_pid=$!
    wait "$check_pid" 2>/dev/null
    { kill "$watchdog_pid"; wait "$watchdog_pid"; } 2>/dev/null
    problems="$(cat "$report_file" 2>/dev/null)"
    rm -f "$report_file"
    if [ -n "$problems" ]; then
      advice="Tell the user about these problems in a few lines at the start of your first reply, with the command that fixes them: \`/unity-dev:toolchain\`, or \`/unity-dev:version-notes\` for the version notes."
      room=$((9800 - ${#context} - ${#advice}))
      if [ "$room" -lt 0 ]; then room=0; fi
      if [ "${#problems}" -gt "$room" ]; then
        problems="$(printf '%s\n' "$problems" | awk -v room="$room" '{ used += length($0) + 1; if (used > room) exit; print }')
(more: /unity-dev:toolchain)"
      fi
      context="$context

$problems
$advice"
    fi
    ;;
esac

# JSON string escaping, character by character, so it behaves the same in every awk. Control characters
# other than tab and newline (such as color codes in a tool's version output) are dropped first.
escaped="$(printf '%s' "$context" | tr -d '\001-\010\013\014\016-\037' | awk '
  function esc(s,   out, i, c) {
    out = ""
    for (i = 1; i <= length(s); i++) {
      c = substr(s, i, 1)
      if (c == "\\") out = out "\\\\"
      else if (c == "\"") out = out "\\\""
      else if (c == "\t") out = out "\\t"
      else if (c != "\r") out = out c
    }
    return out
  }
  { printf "%s%s", (NR > 1 ? "\\n" : ""), esc($0) }
')"

printf '{%s"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$message" "$event" "$escaped"
exit 0
