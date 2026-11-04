#!/usr/bin/env bash
# unity-dev Stop hook. When a turn ends in a project that turned the standards on, it compares what changed with the
# receipts the checks write in docs/proofs/, and asks Claude once to deal with those that fail, are older than the change,
# or don't exist. A family that doesn't apply to the project is listed, with its reason, in docs/proofs/not-applicable.txt.
# It says nothing when the receipts are in order or nothing changed. Always exits 0.

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
. "$root/hooks/common.sh"

input="$(cat)"
case "$input" in
  *'"stop_hook_active":true'* | *'"stop_hook_active": true'*) exit 0 ;;
esac

cwd="$(working_folder "$(hook_cwd "$input")")"
[ "$(standards_state "$cwd")" = on ] || exit 0
project="$(unity_root "$cwd")"
[ -n "$project" ] || project="$(unity_root "${CLAUDE_PROJECT_DIR:-$PWD}")"
[ -n "$project" ] || exit 0

state_dir="${CLAUDE_PLUGIN_DATA:-${TMPDIR:-/tmp}}"
mkdir -p "$state_dir" 2> /dev/null
state="$state_dir/unity-dev-gates-$(printf '%s' "$project" | cksum | cut -d ' ' -f 1)"

previous=""
[ -f "$state" ] && previous="$(cat "$state" 2> /dev/null)"

git_quiet() {
  git -C "$project" -c core.quotePath=false "$@" 2> /dev/null
}

if git_quiet rev-parse --git-dir > /dev/null; then
  head="$(git_quiet rev-parse HEAD || echo none)"
  if [ -z "$previous" ] || [ "$head" = none ]; then
    # The first stop of a project: everything is new to the gate, also what the turn already committed.
    changed="$(git_quiet ls-files -c -o --exclude-standard)"
  else
    changed="$(git_quiet diff --relative --name-only HEAD; git_quiet ls-files -o --exclude-standard)"
  fi
  # Contents, not names: a second edit of a file that is already changed is a new state.
  # Full paths: inside a bigger repository, hash-object reads its list from the repository's root.
  existing="$(printf '%s\n' "$changed" | while IFS= read -r name; do [ -f "$project/$name" ] && printf '%s\n' "$project/$name"; done)"
  hashes="$(printf '%s\n' "$changed"; printf '%s\n' "$existing" | sed '/^$/d' | git -C "$project" hash-object --stdin-paths 2> /dev/null)"
  fingerprint="$head $(printf '%s' "$hashes" | cksum | cut -d ' ' -f 1,2)"
  [ "$previous" = "$fingerprint" ] && exit 0
  old_head="${previous%% *}"
  if [ -n "$old_head" ] && [ "$old_head" != "$head" ] && [ "$old_head" != none ]; then
    changed="$changed
$(git_quiet diff --relative --name-only "$old_head" "$head")"
  fi
else
  # No repository: what is newer than the last stop.
  if [ -f "$state" ]; then
    changed="$(cd "$project" && find Assets Tools -type f -newer "$state" 2> /dev/null)"
  else
    changed="$(cd "$project" && find Assets Tools -type f 2> /dev/null)"
  fi
  [ -n "$changed" ] || exit 0
  fingerprint="no-git"
fi

# The newest changed file per kind, and whether a file of that kind is gone. One pass with builtins only: thousands of
# changed files must stay inside the hook's timeout.
newest_cs=""; newest_ui=""; newest_motion=""; newest_scene=""; newest_data=""; newest_art=""; gone_cs=""; other=""

while IFS= read -r name; do
  [ -n "$name" ] || continue
  kind="${name%.meta}"
  case "$kind" in
    *.md | docs/* | .claude/* | Packages/* | ProjectSettings/* | UserSettings/* | Library/* | Logs/* | Temp/* | */Library/* | */Logs/* | */Temp/*) continue ;;
  esac
  if [ ! -e "$project/$name" ]; then
    case "$kind" in
      *.cs) gone_cs=1 ;;
    esac
    continue
  fi
  case "$kind" in
    *.cs)
      if [ -z "$newest_cs" ] || [ "$project/$name" -nt "$project/$newest_cs" ]; then newest_cs="$name"; fi
      ;;
    *.uxml | *.uss | *.tss)
      if [ -z "$newest_ui" ] || [ "$project/$name" -nt "$project/$newest_ui" ]; then newest_ui="$name"; fi
      ;;
    *.anim | *.controller | *.overrideController | *.mask | *.zanim)
      if [ -z "$newest_motion" ] || [ "$project/$name" -nt "$project/$newest_motion" ]; then newest_motion="$name"; fi
      ;;
    *.unity | *.prefab)
      if [ -z "$newest_scene" ] || [ "$project/$name" -nt "$project/$newest_scene" ]; then newest_scene="$name"; fi
      ;;
    *.asset | *.json)
      if [ -z "$newest_data" ] || [ "$project/$name" -nt "$project/$newest_data" ]; then newest_data="$name"; fi
      ;;
    *.fbx | *.blend | *.glb | *.gltf | *.obj | *.mat | *.shader | *.shadergraph | *.hlsl | *.cginc | *.compute | *.png | *.jpg | *.tga | *.psd | *.py | *.zmesh | Tools/* | */Tools/* | */Art/*)
      if [ -z "$newest_art" ] || [ "$project/$name" -nt "$project/$newest_art" ]; then newest_art="$name"; fi
      ;;
    Assets/* | */Assets/*) other=1 ;;
  esac
done <<NAMES
$changed
NAMES

proofs="$project/docs/proofs"
waivers="$proofs/not-applicable.txt"
failing=""; stale=""; missing=""; waived=""

add_once() { # list, word
  case " $1 " in
    *" $2 "*) printf '%s' "$1" ;;
    *) printf '%s' "${1:+$1 }$2" ;;
  esac
}

# A family's receipts against the newest changed file of a kind, once per family and kind.
check_family() { # family, file (empty: a deletion, compared with the last stop)
  found=""
  for receipt in "$proofs/$1"*; do
    [ -f "$receipt" ] || continue
    found=1
    if grep -q -E '^passed: false|"passed": false' "$receipt" 2> /dev/null; then
      failing="$(add_once "$failing" "$(basename "$receipt")")"
    elif [ -n "$2" ] && [ "$project/$2" -nt "$receipt" ]; then
      stale="$(add_once "$stale" "$(basename "$receipt")")"
    elif [ -z "$2" ] && { [ ! -f "$state" ] || [ "$state" -nt "$receipt" ]; }; then
      stale="$(add_once "$stale" "$(basename "$receipt")")"
    fi
  done
  [ -n "$found" ] && return
  if [ -f "$waivers" ] && grep -q "^$1:" "$waivers" 2> /dev/null; then
    waived="$(add_once "$waived" "$1")"
  else
    missing="$(add_once "$missing" "$1")"
  fi
}

check_kind() { # file, families...
  file="$1"
  shift
  for family in "$@"; do check_family "$family" "$file"; done
}

[ -n "$newest_cs" ] && check_kind "$newest_cs" architecture locomotion crowd balance ui scene-cost off-screen budgets
[ -n "$gone_cs" ] && check_kind "" architecture
[ -n "$newest_ui" ] && check_kind "$newest_ui" ui
[ -n "$newest_motion" ] && check_kind "$newest_motion" inspect_animation locomotion
[ -n "$newest_scene" ] && check_kind "$newest_scene" scene-cost ui study off-screen budgets
[ -n "$newest_data" ] && check_kind "$newest_data" balance scene-cost
[ -n "$newest_art" ] && check_kind "$newest_art" validate_mesh inspect_character inspect_animation study budgets

printf '%s\n' "$fingerprint" > "$state" 2> /dev/null

[ -n "$failing$stale$missing$other" ] || exit 0

message="unity-dev standards: the proofs don't cover this state."
[ -n "$failing" ] && message="$message Failing: $failing."
[ -n "$stale" ] && message="$message Older than what changed: $stale."
[ -n "$missing" ] && message="$message No receipt yet: $missing."
[ -n "$other" ] && message="$message Other assets changed: which proof covers them?"
[ -n "$waived" ] && message="$message Listed as not applicable, is that still true? $waived."
message="$message Each check writes its own receipt in docs/proofs/: run what applies, and fix what fails. A family this project has no use for, or doesn't have yet, goes in docs/proofs/not-applicable.txt as family: reason. Then report the numbers."

printf '{"decision":"block","reason":"%s"}\n' "$message"
exit 0
