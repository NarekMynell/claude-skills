#!/usr/bin/env bash
# unity-dev SessionStart hook: loads the standards in a project that turned them on,
# with UNITY_DEV_STANDARDS=on under "env" in its Claude Code settings. Prints nothing otherwise.
# The standards are skills/standards/SKILL.md up to its "## When the user types the command"
# heading, with ${CLAUDE_SKILL_DIR} resolved. A new session also gets the toolchain check's findings.

[ "$UNITY_DEV_STANDARDS" = on ] || exit 0

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
skill_dir="$root/skills/standards"
[ -f "$skill_dir/SKILL.md" ] || exit 0

input="$(cat)"

standards="$(awk '
  NR == 1 && $0 == "---" { front = 1; next }
  front { if ($0 == "---") front = 0; next }
  /^## When the user types the command/ { exit }
  { print }
' "$skill_dir/SKILL.md")"
standards=${standards//'${CLAUDE_SKILL_DIR}'/"$skill_dir"}

context="The user turned on the unity-dev standards for every session in this project, so they are loaded here as if the user had typed \`/unity-dev:standards\`.

$standards"

case "$input" in
  *'"source":"startup"'* | *'"source": "startup"'*)
    problems="$(bash "$root/skills/toolchain/scripts/check.sh" "${CLAUDE_PROJECT_DIR:-$PWD}" "$CLAUDE_PLUGIN_DATA")"
    if [ -n "$problems" ]; then
      context="$context

$problems
Tell the user about these problems in a few lines at the start of your first reply, with the command that fixes them: \`/unity-dev:toolchain\`, or \`/unity-dev:version-notes\` for the version notes."
    fi
    ;;
esac

# JSON string escaping, character by character, so it behaves the same in every awk.
escaped="$(printf '%s' "$context" | awk '
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

printf '{"systemMessage":"unity-dev standards loaded","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$escaped"
exit 0
