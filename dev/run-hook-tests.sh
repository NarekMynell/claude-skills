#!/usr/bin/env bash
# Runs the plugin's hooks against known inputs in temporary Unity-like git repositories.
# Usage: dev/run-hook-tests.sh
set -u

root="$(cd "$(dirname "$0")/.." && pwd)"
plugin="$root/plugins/unity-dev"
work="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf "$work"' EXIT
failed=0
unset UNITY_DEV_STANDARDS

check() {
  label="$1"; expected="$2"; actual="$3"
  case "$actual" in
    *"$expected"*) echo "ok   $label" ;;
    *) echo "FAIL $label: expected to find [$expected] in [$(printf '%s' "$actual" | cut -c 1-300)]"; failed=1 ;;
  esac
}

absent() {
  label="$1"; unexpected="$2"; actual="$3"
  case "$actual" in
    *"$unexpected"*) echo "FAIL $label: didn't expect [$unexpected] in [$(printf '%s' "$actual" | cut -c 1-300)]"; failed=1 ;;
    *) echo "ok   $label" ;;
  esac
}

empty() {
  label="$1"; actual="$2"
  if [ -z "$actual" ]; then echo "ok   $label"; else echo "FAIL $label: expected nothing, got [$(printf '%s' "$actual" | cut -c 1-300)]"; failed=1; fi
}

standards() { # input, switch, plugin root
  printf '%s' "$1" | UNITY_DEV_STANDARDS="${2:-on}" CLAUDE_PLUGIN_ROOT="${3:-$plugin}" CLAUDE_PROJECT_DIR="$work/none" CLAUDE_PLUGIN_DATA="$work/data" bash "${3:-$plugin}/hooks/standards.sh"
}

json_field() {
  python3 -c "import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1]))" "$1"
}

context_of() {
  printf '%s' "$1" | json_field "d['hookSpecificOutput']['additionalContext']"
}

empty "standards off" "$(standards '{"source":"startup"}' off)"
started="$(standards '{"source":"startup"}')"
check "standards at startup" "SessionStart" "$(printf '%s' "$started" | json_field "d['hookSpecificOutput']['hookEventName']")"
context="$(context_of "$started")"
check "the musts are in the text" "ProjectArchitectureTests" "$context"
case "$context" in *'${'*|*'$ARGUMENTS'*) echo "FAIL unresolved variable"; failed=1 ;; *) echo "ok   variables resolved" ;; esac

# The worst case: a long toolchain report still fits under the 10,000 cap, and the standards stay whole.
long_root="$work/long-plugin"
cp -R "$plugin" "$long_root"
cat > "$long_root/skills/toolchain/scripts/check.sh" <<'CHECK'
#!/usr/bin/env bash
i=0
while [ $i -lt 60 ]; do echo "Problem number $i: a tool is out of date and a long explanation follows it here."; i=$((i + 1)); done
CHECK
worst="$(context_of "$(standards '{"source":"startup"}' on "$long_root")")"
size="$(printf '%s' "$worst" | wc -m | tr -d ' ')"
if [ "$size" -lt 10000 ]; then echo "ok   worst case is $size characters"; else echo "FAIL worst case is $size characters, over the 10,000 cap"; failed=1; fi
check "worst case keeps the standards" "Before reporting a task as done" "$worst"
check "worst case keeps the advice" "/unity-dev:toolchain" "$worst"

subagent="$(standards '{"hook_event_name":"SubagentStart","agent_type":"general-purpose"}')"
check "a subagent gets the standards" "SubagentStart" "$(printf '%s' "$subagent" | json_field "d['hookSpecificOutput']['hookEventName']")"
check "a subagent is told to read its guides" "read the guides" "$(context_of "$subagent")"
empty "a read-only subagent doesn't" "$(standards '{"hook_event_name":"SubagentStart","agent_type":"Explore"}')"

project="$work/parent/project"
mkdir -p "$project/ProjectSettings" "$project/Assets/UI" "$project/Assets/Art" "$project/Assets/My Folder" "$project/.claude" "$project/docs/proofs"
echo "m_EditorVersion: 6000.6.2f1" > "$project/ProjectSettings/ProjectVersion.txt"
echo '{"env":{"UNITY_DEV_STANDARDS":"on"}}' > "$project/.claude/settings.json"
git -C "$project" init -q
git -C "$project" add -A
git -C "$project" -c user.name=t -c user.email=t@t commit -q -m settings

# A session that started above the project has no variable, and finds the switch from where it is now.
from_cwd() {
  printf '{"source":"compact","cwd":"%s"}' "$1" | CLAUDE_PLUGIN_ROOT="$plugin" CLAUDE_PROJECT_DIR="$work/parent" CLAUDE_PLUGIN_DATA="$work/data" bash "$plugin/hooks/standards.sh"
}
check "no variable, inside the project: on" "ProjectArchitectureTests" "$(from_cwd "$project")"
check "no variable, deep inside the project: on" "ProjectArchitectureTests" "$(mkdir -p "$project/Assets/Deep"; from_cwd "$project/Assets/Deep")"
check "no variable, just above the only project: on" "ProjectArchitectureTests" "$(from_cwd "$work/parent")"
empty "no variable, far above the project: off" "$(from_cwd "$work")"
echo '{"env":{"UNITY_DEV_STANDARDS":"off"}}' > "$project/.claude/settings.local.json"
empty "the local settings win" "$(from_cwd "$project")"
rm "$project/.claude/settings.local.json"

gates() { # input, switch, project dir
  printf '%s' "${1:-{\}}" | UNITY_DEV_STANDARDS="${2:-on}" CLAUDE_PLUGIN_ROOT="$plugin" CLAUDE_PROJECT_DIR="${3:-$project}" CLAUDE_PLUGIN_DATA="$work/data" bash "$plugin/hooks/gates.sh"
}

# Run the way a real session does: the switch comes from the project, the place from the hook input.
gates_from_cwd() {
  printf '{"cwd":"%s"}' "$project" | CLAUDE_PLUGIN_ROOT="$plugin" CLAUDE_PROJECT_DIR="$work/parent" CLAUDE_PLUGIN_DATA="$work/data" bash "$plugin/hooks/gates.sh"
}

receipt() { # name, passed
  printf 'passed: %s\n' "${2:-true}" > "$project/docs/proofs/$1"
  sleep 1
}

newer() { # file
  sleep 1
  printf '%s\n' "$RANDOM" >> "$project/$1"
}

empty "gates off" "$(gates '{}' off)"
empty "not a Unity project" "$(gates '{}' on "$work")"
empty "nothing changed" "$(gates '{}')"

waive() { # families not used in the test below
  : > "$project/docs/proofs/not-applicable.txt"
  for family in "$@"; do printf '%s: not in this test\n' "$family" >> "$project/docs/proofs/not-applicable.txt"; done
}
ALL="locomotion crowd balance ui scene-cost off-screen budgets inspect_animation inspect_character study validate_mesh"

printf 'class A {}\n' > "$project/Assets/A.cs"
result="$(gates_from_cwd)"
check "C# without a receipt: valid JSON that blocks, from a session started above" "block" "$(printf '%s' "$result" | json_field "d['decision']")"
check "C# without a receipt: names architecture" "architecture" "$result"
check "C# without a receipt: names every family it can touch" "locomotion crowd balance ui scene-cost off-screen budgets" "$result"
empty "the same state speaks once" "$(gates '{}')"

newer "Assets/A.cs"
check "a second edit of a changed file counts" "architecture" "$(gates '{}')"

printf 'class B {}\n' > "$project/Assets/My Folder/B.cs"
check "a file in a folder with a space counts" "architecture" "$(gates '{}')"

waive $ALL
sleep 1
receipt architecture.txt
newer "Assets/A.cs"
result="$(gates '{}')"
check "a receipt older than the change is named" "Older than what changed: architecture.txt" "$result"
check "waivers are asked about again" "is that still true?" "$result"
sleep 1
receipt architecture.txt
printf 'x\n' >> "$project/README.md"
empty "with a newer passing receipt, nothing to say" "$(gates '{}')"

newer "Assets/A.cs"
receipt architecture.txt false
check "a failing receipt is named" "Failing: architecture.txt" "$(gates '{}')"
receipt architecture.txt
gates '{}' > /dev/null

newer "Assets/A.cs"
empty "a continuation never blocks" "$(gates '{"stop_hook_active":true}')"
receipt architecture.txt
gates '{}' > /dev/null

receipt balance-casual.txt
newer "Assets/A.cs"
check "C# makes an existing balance receipt old" "balance-casual.txt" "$(gates '{}')"
receipt architecture.txt
receipt balance-casual.txt
gates '{}' > /dev/null

printf 'text\n' >> "$project/README.md"
empty "docs alone ask for nothing" "$(gates '{}')"

waive locomotion crowd balance scene-cost off-screen budgets inspect_animation inspect_character study validate_mesh
printf 'x\n' > "$project/Assets/UI/Hud.uxml"
check "UI Toolkit files need a UI receipt" "ui" "$(gates '{}')"
receipt ui-hud.txt
gates '{}' > /dev/null

waive locomotion crowd balance scene-cost off-screen budgets inspect_animation inspect_character study
printf 'x\n' > "$project/Assets/Art/hero.fbx"
git -C "$project" add -A
git -C "$project" -c user.name=t -c user.email=t@t commit -q -m art
check "a commit since the last check still counts" "validate_mesh" "$(gates '{}')"
receipt validate_mesh-hero.json
gates '{}' > /dev/null

mkdir -p "$project/Tools"
printf 'x\n' > "$project/Tools/build_art.py"
check "tools that produce assets count too" "Older than what changed: validate_mesh-hero.json" "$(gates '{}')"
receipt validate_mesh-hero.json
printf '{\n "passed": false\n}\n' > "$project/docs/proofs/inspect_character-hero.json"
newer "Tools/build_art.py"
check "a failing Blender receipt is named" "Failing: inspect_character-hero.json" "$(gates '{}')"
rm "$project/docs/proofs/inspect_character-hero.json"

receipt validate_mesh-hero.json
gates '{}' > /dev/null
printf 'x\n' > "$project/Assets/Art/hero.fbx.meta"
check "import settings in a .meta file count" "validate_mesh-hero.json" "$(gates '{}')"
receipt validate_mesh-hero.json
gates '{}' > /dev/null

waive locomotion crowd balance scene-cost off-screen budgets inspect_character study
printf 'x\n' > "$project/Assets/Clip.zanim"
check "a custom animation file counts" "inspect_animation" "$(gates '{}')"
rm "$project/Assets/Clip.zanim"
waive $ALL
gates '{}' > /dev/null

git -C "$project" add -A
git -C "$project" -c user.name=t -c user.email=t@t commit -q -m all
receipt architecture.txt
gates '{}' > /dev/null
sleep 1
rm "$project/Assets/A.cs"
check "a deleted C# file makes the architecture receipt old" "architecture.txt" "$(gates '{}')"

# The first stop of a project sees what the turn already committed.
built="$work/built"
mkdir -p "$built/ProjectSettings" "$built/Assets" "$built/.claude"
echo "m_EditorVersion: 6000.6.2f1" > "$built/ProjectSettings/ProjectVersion.txt"
printf 'class A {}\n' > "$built/Assets/A.cs"
git -C "$built" init -q
git -C "$built" add -A
git -C "$built" -c user.name=t -c user.email=t@t commit -q -m everything
check "a game built and committed in one turn" "architecture" "$(gates '{}' on "$built")"

# A project inside a bigger repository.
outer="$work/outer"
mkdir -p "$outer/games/nested/ProjectSettings" "$outer/games/nested/Assets"
echo "m_EditorVersion: 6000.6.2f1" > "$outer/games/nested/ProjectSettings/ProjectVersion.txt"
git -C "$outer" init -q
git -C "$outer" add -A
git -C "$outer" -c user.name=t -c user.email=t@t commit -q -m first
gates '{}' on "$outer/games/nested" > /dev/null
printf 'class A {}\n' > "$outer/games/nested/Assets/A.cs"
check "a project inside a bigger repository" "architecture" "$(gates '{}' on "$outer/games/nested")"
git -C "$outer" add -A
gates '{}' on "$outer/games/nested" > /dev/null
printf 'class A { int a; }\n' > "$outer/games/nested/Assets/A.cs"
check "a tracked file changed in a nested project" "architecture" "$(gates '{}' on "$outer/games/nested")"

# No repository at all.
plain="$work/plain"
mkdir -p "$plain/ProjectSettings" "$plain/Assets"
echo "m_EditorVersion: 6000.6.2f1" > "$plain/ProjectSettings/ProjectVersion.txt"
printf 'class A {}\n' > "$plain/Assets/A.cs"
check "a project with no repository" "architecture" "$(gates '{}' on "$plain")"
empty "no repository, nothing new" "$(sleep 1; gates '{}' on "$plain")"

# Thousands of changed files stay inside the timeout.
many="$work/many"
mkdir -p "$many/ProjectSettings" "$many/Assets"
echo "m_EditorVersion: 6000.6.2f1" > "$many/ProjectSettings/ProjectVersion.txt"
git -C "$many" init -q
i=0
while [ $i -lt 2000 ]; do printf 'class A%s {}\n' "$i" > "$many/Assets/A$i.cs"; i=$((i + 1)); done
started=$(date +%s)
result="$(gates '{}' on "$many")"
seconds=$(( $(date +%s) - started ))
check "2,000 changed files" "architecture" "$result"
if [ "$seconds" -lt 15 ]; then echo "ok   2,000 changed files took $seconds s"; else echo "FAIL 2,000 changed files took $seconds s"; failed=1; fi

# A session just above one new project, working in it by full paths.
above="$work/above"
mkdir -p "$above/game/ProjectSettings" "$above/game/Assets" "$above/game/.claude"
echo "m_EditorVersion: 6000.6.2f1" > "$above/game/ProjectSettings/ProjectVersion.txt"
echo '{"env":{"UNITY_DEV_STANDARDS":"on"}}' > "$above/game/.claude/settings.json"
printf 'class A {}\n' > "$above/game/Assets/A.cs"
git -C "$above/game" init -q
below() {
  printf '{"cwd":"%s"}' "$above" | CLAUDE_PLUGIN_ROOT="$plugin" CLAUDE_PROJECT_DIR="$above" CLAUDE_PLUGIN_DATA="$work/data" bash "$plugin/hooks/gates.sh"
}
check "the one project below the session's folder" "architecture" "$(below)"
mkdir -p "$above/other/ProjectSettings"
echo "m_EditorVersion: 6000.6.2f1" > "$above/other/ProjectSettings/ProjectVersion.txt"
printf 'class B {}\n' > "$above/game/Assets/B.cs"
empty "two projects below: it doesn't guess" "$(below)"

# Receipts are written by the checks.
edit_hook() { # path
  printf '{"tool_name":"Write","tool_input":{"file_path":"%s"},"cwd":"%s"}' "$1" "$project" | CLAUDE_PLUGIN_ROOT="$plugin" bash "$plugin/hooks/receipts.sh"
}
check "writing a receipt by hand is refused" "deny" "$(edit_hook "$project/docs/proofs/architecture.txt" | json_field "d['hookSpecificOutput']['permissionDecision']")"
empty "the list of what doesn't apply can be edited" "$(edit_hook "$project/docs/proofs/not-applicable.txt")"
empty "any other file costs nothing" "$(edit_hook "$project/Assets/A.cs")"

[ "$failed" = 0 ] && echo "all hook tests passed"
exit "$failed"
