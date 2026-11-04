# Shared by the unity-dev hooks. Sourced, not run.

# The folder a hook input says the session is in, else the project's folder, else this process's.
hook_cwd() {
  found="$(printf '%s' "$1" | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
  printf '%s' "${found:-${CLAUDE_PROJECT_DIR:-$PWD}}"
}

# on or off. The variable when this session has it. A session started above a project has it unset even after moving
# into the project, as when new-project creates one, so the project's own settings are read too: local before shared.
standards_state() {
  case "$UNITY_DEV_STANDARDS" in
    on | off) printf '%s' "$UNITY_DEV_STANDARDS"; return ;;
  esac
  dir="$1"
  while [ -n "$dir" ] && [ "$dir" != "/" ] && [ "$dir" != "." ]; do
    for file in "$dir/.claude/settings.local.json" "$dir/.claude/settings.json"; do
      [ -f "$file" ] || continue
      value="$(sed -n 's/.*"UNITY_DEV_STANDARDS"[[:space:]]*:[[:space:]]*"\([a-z]*\)".*/\1/p' "$file" | head -n 1)"
      if [ -n "$value" ]; then
        printf '%s' "$value"
        return
      fi
    done
    dir="$(dirname "$dir")"
  done
}

# The Unity project around a folder, or nothing.
unity_root() {
  dir="$1"
  while [ -n "$dir" ] && [ "$dir" != "/" ] && [ "$dir" != "." ]; do
    if [ -f "$dir/ProjectSettings/ProjectVersion.txt" ]; then
      printf '%s' "$dir"
      return
    fi
    dir="$(dirname "$dir")"
  done
}

# A session that started just above a new project and works in it by full paths: the one Unity project directly below a
# folder, and only when there is exactly one, so a folder of many projects never picks the wrong one.
only_project_below() {
  found=""
  for version in "$1"/*/ProjectSettings/ProjectVersion.txt; do
    [ -f "$version" ] || continue
    [ -z "$found" ] || return 0
    found="${version%/ProjectSettings/ProjectVersion.txt}"
  done
  printf '%s' "$found"
}

# Where the hooks work: the project around the session's folder, else the one directly below it, else the folder itself.
working_folder() {
  around="$(unity_root "$1")"
  if [ -n "$around" ]; then
    printf '%s' "$around"
    return
  fi
  below="$(only_project_below "$1")"
  printf '%s' "${below:-$1}"
}
