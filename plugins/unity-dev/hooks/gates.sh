#!/usr/bin/env bash
# unity-dev Stop hook. When a turn ends in a Unity project with unity-dev on, it compares what changed since the last stop with the
# receipts the checks write in docs/proofs/, and asks Claude once to deal with those the change can have made wrong: failing, older
# than the change, or missing. Only those: it costs a turn each time it speaks, and one that always speaks is one nobody hears.
#   - C# and assembly definitions ask for the architecture check.
#   - A model or a clip asks for the receipts named after it, not those of the other 72.
#   - A check of the whole game answers for its own area, by the file's kind or by words in its path, or after many changes.
# A family is asked for only where the skill whose must it proves is on (family_on): models need modeling, balance game-design.
# A family that doesn't apply to the project is listed, with its reason, in docs/proofs/not-applicable.txt, and so is a failing receipt
# the user accepted, with their words. A failure, or a proof many changes have made old, is told once in a session until it changes.
# It says nothing when the receipts are in order or nothing changed. Always exits 0.

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
hooks_dir="$root/hooks"
[ -f "$hooks_dir/domains.txt" ] || exit 0
. "$hooks_dir/lib.sh"

input="$(cat)"
session="$(printf '%s' "$input" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
case "$input" in
  *'"stop_hook_active":true'* | *'"stop_hook_active": true'*) exit 0 ;;
esac

cwd="$(working_folder "$(hook_cwd "$input")")"
load_domains
load_settings "$cwd"
any_switch && domain_active unity-dev || exit 0

# The skill whose must a family of receipts proves.
family_on() { # family
  case "$1" in
    architecture) skill_on unity-dev code-standards ;;
    ui) skill_on unity-dev ui-quality ;;
    locomotion) skill_on unity-dev animation ;;
    crowd) skill_on unity-dev npc-behavior ;;
    scene-cost | off-screen | budgets) skill_on unity-dev performance ;;
    colliders) skill_on unity-dev models ;;
    balance) skill_on game-design game-design ;;
    study) skill_on game-design art-direction ;;
    validate_mesh) skill_on modeling models || skill_on modeling characters ;;
    inspect_character) skill_on modeling characters ;;
    inspect_animation) skill_on modeling animation ;;
    *) return 0 ;;
  esac
}

project="$(unity_root "$cwd")"
[ -n "$project" ] || project="$(unity_root "${CLAUDE_PROJECT_DIR:-$PWD}")"
[ -n "$project" ] || exit 0

state_dir="${CLAUDE_PLUGIN_DATA:-${TMPDIR:-/tmp}}"
mkdir -p "$state_dir" 2> /dev/null
# The last stop: its time is the file's, its commit the content. Moved in place after looking, so a stop killed later doesn't look again.
state="$state_dir/unity-dev-gates-$(printf '%s' "$project" | cksum | cut -d ' ' -f 1)"
mark="$state.now"
: > "$mark" 2> /dev/null

git_quiet() {
  git -C "$project" -c core.quotePath=false "$@" 2> /dev/null
}

first_stop=""
[ -f "$state" ] || first_stop=1
if git_quiet rev-parse --git-dir > /dev/null; then
  head="$(git_quiet rev-parse --verify -q HEAD)"
  previous="$(cat "$state" 2> /dev/null)"
  if [ -n "$first_stop" ] || [ -z "$head" ]; then
    # The first stop of a project: everything is new to the gate, also what the turn already committed.
    changed="$(git_quiet ls-files -c -o --exclude-standard)"
  else
    changed="$(git_quiet diff --relative --name-only --no-renames HEAD; git_quiet ls-files -o --exclude-standard)"
    if [ -n "$previous" ] && [ "$previous" != "$head" ]; then
      changed="$changed
$(git_quiet diff --relative --name-only --no-renames "$previous" "$head")"
    elif [ -z "$previous" ]; then
      # The repository's first commit came since the last stop: what it holds may have changed in that time.
      changed="$changed
$(git_quiet ls-files -c)"
    fi
  fi
else
  head=""
  changed="$(cd "$project" && find Assets Tools -type f 2> /dev/null)"
fi

SWEEP=30
shopt -s nocasematch
newest_cs=""; gone_cs=""; newest_ui=""; newest_motion=""; newest_balance=""; newest_scene=""; newest_tool=""
newest_uxml=""; newest_clip_file=""; assets=""; clips=""; characters=""; counted=0; touched=""

set_newer() { # variable, file: keeps the newer of the two, with no process per file
  eval "current=\$$1"
  if [ -z "$current" ] || [ "$project/$2" -nt "$project/$current" ]; then eval "$1=\$2"; fi
}

while IFS= read -r name; do
  case "$name" in
    "" | *.meta | *.md | docs/* | .claude/* | ProjectSettings/* | UserSettings/* | Library/* | Logs/* | Temp/*) continue ;;
    Packages/*.cs | Packages/*.asmdef) ;;
    Packages/*) continue ;;
  esac
  if [ ! -e "$project/$name" ]; then
    case "$name" in
      *.cs | *.asmdef)
        # A deletion leaves its time on the folder it was in.
        folder="$project/${name%/*}"
        if [ -n "$first_stop" ] || [ ! -d "$folder" ] || [ ! "$state" -nt "$folder" ]; then gone_cs="$folder"; touched=1; fi
        ;;
    esac
    continue
  fi
  # In the same second as the last stop counts: it is looked at once more, and missed never.
  [ -n "$first_stop" ] || [ ! "$state" -nt "$project/$name" ] || continue
  case "$name" in
    Assets/* | */Assets/* | Tools/* | */Tools/* | Packages/*) touched=1 ;;
  esac
  counted=$((counted + 1))
  area=""
  case "$name" in
    */ui/* | */hud/* | *screen* | *panel* | *popup* | *menu* | *hud*) area="$area ui" ;;
  esac
  case "$name" in
    */motion/* | *locomot* | *movement* | */mover* | *walk* | *npc* | */actor* | *crowd* | *agent* | *animal* | *visitor* | *character* | *animation* | *gait* | *playercontroller*) area="$area motion" ;;
  esac
  case "$name" in
    *balance* | *economy* | *pacing* | *progress* | *reward* | *upgrade* | *price* | *shop* | *simulat*) area="$area balance" ;;
  esac
  case "$name" in
    *.cs | *.asset | *.json | *.prefab | *.unity)
      case "$area" in *ui*) set_newer newest_ui "$name" ;; esac
      case "$area" in *motion*) set_newer newest_motion "$name" ;; esac
      case "$area" in *balance*) set_newer newest_balance "$name" ;; esac
      ;;
  esac
  case "$name" in
    *.cs | *.asmdef) set_newer newest_cs "$name" ;;
    *.uxml | *.uss | *.tss)
      set_newer newest_ui "$name"
      set_newer newest_uxml "$name"
      ;;
    *.anim | *.controller | *.overrideController | *.mask | *.zanim)
      set_newer newest_motion "$name"
      set_newer newest_clip_file "$name"
      case "$name" in *.anim | *.zanim) clips="$clips
$name" ;; esac
      ;;
    *.unity | *.prefab) set_newer newest_scene "$name" ;;
    *.fbx | *.blend | *.glb | *.gltf | *.obj | *.zmesh)
      # What the project's own art folder holds. A store pack beside it answers to its seller.
      case "$name" in
        Assets/_Project/*) ;;
        *) [ -d "$project/Assets/_Project" ] && continue ;;
      esac
      assets="$assets
$name"
      case "$area" in *motion*) characters="$characters
$name" ;; esac
      case "$name" in *@*) clips="$clips
$name" ;; esac
      ;;
    *.py | Tools/* | */Tools/*) set_newer newest_tool "$name" ;;
  esac
done <<NAMES
$changed
NAMES

previous_state=""
[ -f "$state" ] && previous_state="$state"
keep_time="$state.before"
[ -n "$previous_state" ] && mv -f "$state" "$keep_time" 2> /dev/null
printf '%s\n' "$head" > "$mark" 2> /dev/null
mv -f "$mark" "$state" 2> /dev/null

# Nothing that a proof answers for changed since the last stop. A document, a bare commit: nothing to ask.
[ -n "$touched" ] || { rm -f "$keep_time"; exit 0; }

proofs="$project/docs/proofs"
waivers="$proofs/not-applicable.txt"
failing=""; stale=""; missing=""; missing_files=""; waived=""; reconsider=""; known=0
told="$state.told"
nl='
'
all_failing=""
[ -d "$proofs" ] && all_failing="$nl$(grep -l -E '^passed: false|"passed": false' "$proofs"/* 2> /dev/null | sed 's#.*/##')$nl"

add_once() { # list, word
  case " $1 " in
    *" $2 "*) printf '%s' "$1" ;;
    *) printf '%s' "${1:+$1 }$2" ;;
  esac
}

in_family() { # receipt name, family
  case "$1" in
    "$2" | "$2".* | "$2"-*) return 0 ;;
  esac
  return 1
}

waived_family() { # family
  [ -f "$waivers" ] && grep -q "^$1:" "$waivers" 2> /dev/null
}

told_before() { # what, told already in this session? Remembers it if not.
  line="$session|$1"
  if [ -f "$told" ] && grep -q -F -x -- "$line" "$told" 2> /dev/null; then return 0; fi
  printf '%s\n' "$line" >> "$told" 2> /dev/null
  return 1
}

# A failing receipt is told once in a session until it changes, or its acceptance noted. Says whether it can be compared.
read_receipt() { # receipt name
  case "$all_failing" in
    *"$nl$1$nl"*) ;;
    *) return 0 ;;
  esac
  if [ -f "$waivers" ] && grep -q "^${1%.*}:" "$waivers" 2> /dev/null; then
    waived="$(add_once "$waived" "${1%.*}")"
    return 0
  fi
  if told_before "failing|$1|$(cksum < "$proofs/$1" | cut -d ' ' -f 1,2)"; then
    known=$((known + 1))
  else
    failing="$(add_once "$failing" "$1")"
  fi
  return 1
}

# Something of the family's own kind appeared since "no use for it" was written: is that still so? Once in a session.
question_waiver() { # family, file
  [ -n "$2" ] && [ "$project/$2" -nt "$waivers" ] || return 0
  told_before "waiver|$1" || reconsider="$(add_once "$reconsider" "$1")"
}

# A family's receipts against the newest changed file of its area.
check_family() { # family, file (empty: a deletion, given in `gone_cs`), file of the family's own kind, if any
  family_on "$1" || return 0
  found=""
  for receipt in "$proofs"/*; do
    [ -f "$receipt" ] || continue
    name="${receipt##*/}"
    in_family "$name" "$1" || continue
    found=1
    read_receipt "$name" || continue
    # A check of the whole parts comes before the cut, so before the file is saved. The final check holds it to the character.
    case "$name" in
      *-parts.*) continue ;;
    esac
    if [ -n "$2" ]; then
      if [ "$project/$2" -nt "$receipt" ]; then stale="$(add_once "$stale" "$name")"; fi
    elif [ ! -d "$gone_cs" ] || [ "$gone_cs" -nt "$receipt" ]; then
      stale="$(add_once "$stale" "$name")"
    fi
  done
  [ -n "$found" ] && return
  if waived_family "$1"; then
    waived="$(add_once "$waived" "$1")"
    [ -z "${3:-}" ] || question_waiver "$1" "$3"
  else
    missing="$(add_once "$missing" "$1")"
  fi
}

# Whether a receipt's name after the family means this file: Crate for Crate.fbx and for Crate_LOD0.fbx, visitor-Walk for Hero@Walk.fbx.
names_file() { # stem, plain
  case "$1" in
    "$2" | "$2"[-_.@]* | *[-_.@]"$2" | *[-_.@]"$2"[-_.@]*) return 0 ;;
  esac
  case "$2" in
    "$1"[-_.@]*) return 0 ;;
  esac
  return 1
}

# Models and clips: each file against the receipts named after it.
check_files() { # family, list of files
  family_on "$1" || return 0
  while IFS= read -r file; do
    [ -n "$file" ] || continue
    plain="${file##*/}"
    plain="${plain%.*}"
    plain="${plain#*@}"
    matched=""
    for receipt in "$proofs"/*; do
      [ -f "$receipt" ] || continue
      name="${receipt##*/}"
      in_family "$name" "$1" || continue
      stem="${name%.*}"
      stem="${stem#"$1"}"
      stem="${stem#-}"
      stem="${stem%-parts}"
      names_file "$stem" "$plain" || continue
      matched=1
      read_receipt "$name" || continue
      case "$name" in
        *-parts.*) continue ;;
      esac
      if [ "$project/$file" -nt "$receipt" ]; then stale="$(add_once "$stale" "$name")"; fi
    done
    [ -n "$matched" ] && continue
    if waived_family "$1"; then
      waived="$(add_once "$waived" "$1")"
      question_waiver "$1" "$file"
    else
      missing_files="$(add_once "$missing_files" "$1:$(printf '%s' "$plain" | tr ' ' '_')")"
    fi
  done <<FILES
$2
FILES
}

# A tool that makes assets: some receipt has to have come after it.
check_tool() { # family, file
  family_on "$1" || return 0
  newest=""
  for receipt in "$proofs"/*; do
    [ -f "$receipt" ] || continue
    name="${receipt##*/}"
    in_family "$name" "$1" || continue
    case "$name" in *-parts.*) continue ;; esac
    if [ -z "$newest" ] || [ "$receipt" -nt "$newest" ]; then newest="$receipt"; fi
  done
  [ -n "$newest" ] || return
  if [ "$project/$2" -nt "$newest" ]; then stale="$(add_once "$stale" "${newest##*/}")"; fi
}

if [ -n "$newest_cs" ]; then check_family architecture "$newest_cs" "$newest_cs"; fi
if [ -n "$gone_cs" ]; then check_family architecture ""; fi
if [ -n "$newest_ui" ]; then check_family ui "$newest_ui" "$newest_uxml"; fi
if [ -n "$newest_motion" ]; then
  check_family locomotion "$newest_motion" "$newest_clip_file"
  case "$newest_motion" in *.cs) check_family crowd "$newest_motion" ;; esac
fi
if [ -n "$newest_balance" ]; then check_family balance "$newest_balance"; fi
if [ -n "$newest_scene" ]; then
  check_family scene-cost "$newest_scene" "$newest_scene"
  check_family colliders "$newest_scene" "$newest_scene"
fi
if [ -n "$assets" ]; then check_files validate_mesh "$assets"; fi
if [ -n "$clips" ]; then check_files inspect_animation "$clips"; fi
if [ -n "$newest_tool" ]; then
  for family in validate_mesh inspect_character inspect_animation; do check_tool "$family" "$newest_tool"; done
fi

# A character is whatever has a rig, wherever it sits and whatever its name: an FBX says so in plain text. Others have a receipt or a word in the path.
rigged=0
while IFS= read -r file; do
  [ -n "$file" ] || continue
  case "$file" in
    *.fbx)
      if [ "$rigged" -lt 50 ]; then
        rigged=$((rigged + 1))
        if grep -q -a 'LimbNode' "$project/$file" 2> /dev/null; then
          case "$nl$characters$nl" in *"$nl$file$nl"*) ;; *) characters="$characters
$file" ;; esac
        fi
      fi
      ;;
  esac
  plain="${file##*/}"
  plain="${plain%.*}"
  for receipt in "$proofs"/*; do
    [ -f "$receipt" ] || continue
    name="${receipt##*/}"
    in_family "$name" inspect_character || continue
    stem="${name%.*}"
    stem="${stem#inspect_character-}"
    stem="${stem%-parts}"
    if names_file "$stem" "$plain"; then
      case "$nl$characters$nl" in *"$nl$file$nl"*) ;; *) characters="$characters
$file" ;; esac
    fi
  done
done <<FILES
$assets
FILES
if [ -n "$characters" ]; then check_files inspect_character "$characters"; fi

# After many changes any proof is old, and one nobody ever ran is missing: a game built in one long turn, or over many short ones,
# answers for all of them. Told once in a session each: rerunning a whole simulation is the user's time.
if [ -d "$project/Assets/_Project" ]; then roots="$project/Assets/_Project"; else roots="$project/Assets"; fi
[ -d "$project/Tools" ] && roots="$roots
$project/Tools"

many_since() { # file
  count="$(printf '%s\n' "$roots" | while IFS= read -r folder; do
    find "$folder" -type f ! -name '*.meta' -newer "$1" 2> /dev/null
  done | head -n "$SWEEP" | wc -l | tr -d ' ')"
  [ "$count" -ge "$SWEEP" ]
}

sweep="$state.sweep"
missing_sweep=""
if [ -n "$first_stop" ]; then
  [ "$counted" -lt "$SWEEP" ] || missing_sweep=1
  : > "$sweep" 2> /dev/null
elif [ ! -f "$sweep" ]; then
  : > "$sweep" 2> /dev/null
elif many_since "$sweep"; then
  missing_sweep=1
  : > "$sweep" 2> /dev/null
fi

for family in architecture locomotion crowd balance ui scene-cost colliders off-screen budgets inspect_animation inspect_character study validate_mesh; do
  family_on "$family" || continue
  newest=""
  for receipt in "$proofs"/*; do
    [ -f "$receipt" ] || continue
    name="${receipt##*/}"
    in_family "$name" "$family" || continue
    case "$name" in *-parts.*) continue ;; esac
    if [ -z "$newest" ] || [ "$receipt" -nt "$newest" ]; then newest="$receipt"; fi
  done
  if [ -z "$newest" ]; then
    if [ -n "$missing_sweep" ] && ! waived_family "$family"; then missing="$(add_once "$missing" "$family")"; fi
  elif many_since "$newest" && ! told_before "sweep|${newest##*/}"; then
    read_receipt "${newest##*/}" && stale="$(add_once "$stale" "${newest##*/}")"
  fi
done

rm -f "$keep_time"

[ -n "$failing$stale$missing$missing_files$reconsider" ] || exit 0

# The first names and a count: a hook's message has little room.
named() {
  set -- $1
  total=$#
  if [ "$total" -gt 5 ]; then
    printf '%s %s %s %s %s and %s more' "$1" "$2" "$3" "$4" "$5" "$((total - 5))"
  else
    printf '%s' "$*"
  fi
}

message="unity-dev standards: the proofs don't cover this state."
[ -n "$failing" ] && message="$message Failing: $(named "$failing"). Read each receipt's issues and examples; tell the user once, in plain words, what the player would see and what you propose; don't just name the check."
[ "$known" -gt 0 ] && message="$message Still failing, already told: $known."
[ -n "$stale" ] && message="$message Older than what changed: $(named "$stale")."
[ -n "$missing" ] && message="$message No receipt yet: $missing."
[ -n "$missing_files" ] && message="$message No receipt named after the file: $(named "$missing_files")."
[ -n "$waived" ] && message="$message Listed as not applicable, is that still true? $(named "$waived")."
message="$message Each check writes its own receipt in docs/proofs/: run what this change can have broken, and fix what fails. A family this project has no use for, or doesn't have yet, goes in docs/proofs/not-applicable.txt as family: reason; a failing receipt the user accepted, as receipt-name: their words. Then report the numbers."

message="$(printf '%s' "$message" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"
printf '{"decision":"block","reason":"%s"}\n' "$message"
exit 0
