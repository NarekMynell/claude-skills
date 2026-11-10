# Shared by the hooks of every domain plugin in this marketplace. Sourced, not run.
# The source is shared/hooks/ at the repository's root: dev/sync.py copies it into each plugin's hooks/, because a plugin
# can't read another plugin's files. Edit the source, never a copy.
#
# A project turns domains and skills on or off under "env" in its .claude/settings.json, and per person in
# .claude/settings.local.json, which wins key by key:
#   <DOMAIN>_STANDARDS = on | off          a domain: all its skills (UNITY_DEV_STANDARDS for unity-dev)
#   <DOMAIN>_SKILL_<SKILL> = on | off      one skill, whatever its domain's switch says (UNITY_DEV_SKILL_VFX)
# A domain whose switch is not set is on wherever a domain that builds on it is on: game-design and modeling come with
# unity-dev. A single skill brings no other domain. Core is the base: it loads wherever any domain is active (any of its
# skills on), and can't be switched off while one is; its own guides can.
#
# Every function sets variables instead of printing, so no subshell is spent on them: the hooks run on every prompt.

nl='
'

# --- Where the session works ---

# The folder a hook input says the session is in, else the project's folder, else this process's.
hook_cwd() { # input
  found="$(printf '%s' "$1" | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
  printf '%s' "${found:-${CLAUDE_PROJECT_DIR:-$PWD}}"
}

parent_of() { # folder: the parent, or nothing above the root
  case "$1" in
    */*) dir="${1%/*}" ;;
    *) dir="" ;;
  esac
}

# The Unity project around a folder, or nothing.
unity_root() { # folder
  dir="$1"
  while [ -n "$dir" ] && [ "$dir" != "/" ] && [ "$dir" != "." ]; do
    if [ -f "$dir/ProjectSettings/ProjectVersion.txt" ]; then
      printf '%s' "$dir"
      return
    fi
    parent_of "$dir"
  done
}

# A session that started just above a new project and works in it by full paths: the one Unity project directly below a
# folder, and only when there is exactly one, so a folder of many projects never picks the wrong one.
only_project_below() { # folder
  found=""
  for version in "$1"/*/ProjectSettings/ProjectVersion.txt; do
    [ -f "$version" ] || continue
    [ -z "$found" ] || return 0
    found="${version%/ProjectSettings/ProjectVersion.txt}"
  done
  printf '%s' "$found"
}

# Where the hooks work: the Unity project around the session's folder, else the one directly below it, else the folder itself.
working_folder() { # folder
  around="$(unity_root "$1")"
  if [ -n "$around" ]; then
    printf '%s' "$around"
    return
  fi
  below="$(only_project_below "$1")"
  printf '%s' "${below:-$1}"
}

# --- The domains: domains.txt next to this file, "domain|PREFIX|domains it builds on|skill=SKILL ..." per line ---

base=core

load_domains() {
  domains=""
  prefixes=" "
  while IFS='|' read -r name prefix deps skills; do
    case "$name" in "" | "#"*) continue ;; esac
    domains="${domains:+$domains }$name"
    prefixes="$prefixes$name=$prefix "
    eval "deps_$prefix=\$deps; skills_$prefix=\$skills"
  done < "$hooks_dir/domains.txt"
}

prefix_of() { # domain: sets prefix, UNITY_DEV for unity-dev, or nothing for an unknown domain
  prefix=""
  case "$prefixes" in
    *" $1="*)
      prefix="${prefixes#* $1=}"
      prefix="${prefix%% *}"
      ;;
  esac
}

deps_of() { # domain: sets deps
  prefix_of "$1"
  deps=""
  [ -n "$prefix" ] && eval "deps=\$deps_$prefix"
}

skill_pairs_of() { # domain: sets pairs, "skill=SKILL ..."
  prefix_of "$1"
  pairs=""
  [ -n "$prefix" ] && eval "pairs=\$skills_$prefix"
}

# --- Switches ---

# The switches the settings files set, as NAME=on lines: from the folder up, nearest first, personal before shared, so the
# first line for a name decides it. A session started above a project has none of the project's variables.
load_settings() { # folder
  files=""
  dir="$1"
  while [ -n "$dir" ] && [ "$dir" != "/" ] && [ "$dir" != "." ]; do
    for file in "$dir/.claude/settings.local.json" "$dir/.claude/settings.json"; do
      [ -f "$file" ] && files="$files$file$nl"
    done
    parent_of "$dir"
  done
  switches=""
  [ -n "$files" ] || return 0
  switches="$(printf '%s' "$files" | while IFS= read -r file; do
    grep -oE '"[A-Z][A-Z0-9_]*"[[:space:]]*:[[:space:]]*"(on|off)"' "$file" 2> /dev/null
  done | sed -E 's/^"([A-Z0-9_]+)"[[:space:]]*:[[:space:]]*"(on|off)"$/\1=\2/')"
}

# Sets value: on, off, or nothing when unset. The session's variable first, then the settings files.
switch_value() { # variable name
  value=""
  case "$1" in *[!A-Z0-9_]* | "") return ;; esac
  eval "value=\${$1:-}"
  case "$value" in on | off) return ;; esac
  value=""
  case "$nl$switches$nl" in
    *"$nl$1="*)
      value="${nl}${switches}${nl}"
      value="${value#*"$nl$1="}"
      value="${value%%"$nl"*}"
      ;;
  esac
}

# Sets flag, on or off: the domain's own switch, else whether a domain that builds on it is on. The base is on wherever
# another domain is active, whatever its switch says. Remembered per run.
domain_flag() { # domain
  local own dependent dependent_deps
  prefix_of "$1"
  [ -n "$prefix" ] || { flag=off; return; }
  eval "flag=\${flag_$prefix:-}"
  [ -z "$flag" ] || return 0
  switch_value "${prefix}_STANDARDS"
  own="$value"
  if [ "$1" = "$base" ]; then
    [ "$own" = on ] || { if others_active; then own=on; else own=off; fi; }
  elif [ -z "$own" ]; then
    own=off
    for dependent in $domains; do
      deps_of "$dependent"
      dependent_deps="$deps"
      case " $dependent_deps " in
        *" $1 "*)
          domain_flag "$dependent"
          if [ "$flag" = on ]; then own=on; break; fi
          ;;
      esac
    done
  fi
  prefix_of "$1"
  eval "flag_$prefix=\$own"
  flag="$own"
}

# Whether a domain other than the base has a skill on.
others_active() {
  local other
  for other in $domains; do
    [ "$other" = "$base" ] && continue
    domain_active "$other" && return 0
  done
  return 1
}

# Sets on_skills: the domain's skills that are on, each by its own switch, else by its domain's. Remembered per run.
active_skills() { # domain
  local pair skill upper list domain_prefix
  prefix_of "$1"
  [ -n "$prefix" ] || { on_skills=""; return; }
  domain_prefix="$prefix"
  eval "on_skills=\${active_$domain_prefix-unset}"
  [ "$on_skills" = unset ] || return 0
  skill_pairs_of "$1"
  list=""
  for pair in $pairs; do
    skill="${pair%%=*}"
    upper="${pair#*=}"
    switch_value "${domain_prefix}_SKILL_$upper"
    if [ -z "$value" ]; then
      domain_flag "$1"
      value="$flag"
    fi
    [ "$value" = on ] && list="${list:+$list }$skill"
  done
  eval "active_$domain_prefix=\$list"
  on_skills="$list"
}

domain_active() { # domain
  active_skills "$1"
  [ -n "$on_skills" ]
}

# Whether a domain's standards load: any of its skills is on, or it is the base and another domain is active.
domain_loads() { # domain
  domain_active "$1" && return 0
  [ "$1" = "$base" ] && others_active
}

# Whether one skill is on.
skill_on() { # domain, skill
  active_skills "$1"
  case " $on_skills " in *" $2 "*) return 0 ;; esac
  return 1
}

# Whether a domain builds on another, directly or through others.
builds_on() { # domain, the one it may build on
  local dep list
  deps_of "$1"
  list="$deps"
  for dep in $list; do
    [ "$dep" = "$2" ] && return 0
    builds_on "$dep" "$2" && return 0
  done
  return 1
}

# Whether any switch of the marketplace is set at all: most sessions have none, and the hooks stop there.
any_switch() {
  local name pair
  for name in $domains; do
    prefix_of "$name"
    switch_value "${prefix}_STANDARDS"
    [ -n "$value" ] && return 0
    skill_pairs_of "$name"
    for pair in $pairs; do
      switch_value "${prefix}_SKILL_${pair#*=}"
      [ -n "$value" ] && return 0
    done
  done
  return 1
}

# --- What reaches Claude ---

# Sets hub: the domain's standards, skills/standards/SKILL.md up to "## When the user types the command", without the rows
# of tables whose first link names a skill of the domain that is off, with the paths made absolute.
hub_text() { # plugin root, skills that are on, all skills of the domain
  hub="$(awk -v on=" $2 " -v all=" $3 " '
    NR == 1 && $0 == "---" { front = 1; next }
    front { if ($0 == "---") front = 0; next }
    /^## When the user types the command/ { exit }
    /^\|/ && match($0, /\]\(\.\.\/[a-z0-9-]+\//) {
      skill = substr($0, RSTART + 5, RLENGTH - 6)
      if (index(all, " " skill " ") && !index(on, " " skill " ")) next
    }
    { print }
  ' "$1/skills/standards/SKILL.md")"
  hub="${hub//'${CLAUDE_SKILL_DIR}'/"$1/skills/standards"}"
  hub="${hub//'${CLAUDE_PLUGIN_ROOT}'/"$1"}"
}

input_field() { # input, field
  printf '%s' "$1" | sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" | head -n 1
}

# The domain a prompt's standards command names: unity-dev for "/unity-dev:standards build a level". Nothing for
# "/unity-dev:standards off" or "on", which only change a switch.
prompt_domain() { # input
  printf '%s' "$1" | sed -n 's/.*"prompt"[[:space:]]*:[[:space:]]*"[[:space:]]*\/\([a-z0-9-]*\):standards\([" \\].*\)/\1 \2/p' | head -n 1 | {
    read -r found rest
    case "$rest" in
      'on"'* | 'off"'*) ;;
      *) printf '%s' "$found" ;;
    esac
  }
}

# Sessions that have this domain's standards in context, so a later prompt doesn't add them again.
marks_file() {
  printf '%s' "${CLAUDE_PLUGIN_DATA:-${TMPDIR:-/tmp}}/loaded-sessions-$self"
}
marked() { # session
  [ -n "$1" ] && grep -qxF -- "$1" "$(marks_file)" 2> /dev/null
}
mark() { # session
  local file
  [ -n "$1" ] || return 0
  file="$(marks_file)"
  mkdir -p "${file%/*}" 2> /dev/null
  marked "$1" || printf '%s\n' "$1" >> "$file" 2> /dev/null
  if [ "$(wc -l < "$file" 2> /dev/null | tr -d ' ')" -gt 400 ] 2> /dev/null; then
    tail -n 200 "$file" > "$file.tmp" 2> /dev/null && mv -f "$file.tmp" "$file" 2> /dev/null
  fi
}

# JSON string escaping, character by character, so it behaves the same in every awk. Control characters other than tab
# and newline (such as color codes in a tool's version output) are dropped first.
json_escape() {
  LC_ALL=C tr -d '\001-\010\013\014\016-\037' | LC_ALL=C awk '
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
  '
}
