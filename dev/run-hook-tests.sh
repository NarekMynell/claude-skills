#!/usr/bin/env bash
# Runs the plugins' hooks against known inputs in temporary projects and Unity-like git repositories.
# Usage: dev/run-hook-tests.sh
set -u

root="$(cd "$(dirname "$0")/.." && pwd)"
plugins="$root/plugins"
plugin="$plugins/unity-dev"
work="$(cd "$(mktemp -d)" && pwd -P)"
trap 'rm -rf "$work"' EXIT
failed=0
# The switches of the session running the tests mustn't decide them.
for variable in $(env | cut -d = -f 1 | grep -E '_STANDARDS$|_SKILL_'); do unset "$variable"; done

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
  printf '%s' "$1" | UNITY_DEV_STANDARDS="${2:-on}" CLAUDE_PLUGIN_ROOT="${3:-$plugin}" CLAUDE_PROJECT_DIR="$work/none" CLAUDE_PLUGIN_DATA="$work/data" bash "${3:-$plugin}/hooks/context.sh" unity-dev
}

json_field() {
  python3 -c "import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1]))" "$1"
}

context_of() {
  printf '%s' "$1" | json_field "d['hookSpecificOutput']['additionalContext']"
}

empty "standards off" "$(standards '{"hook_event_name":"SessionStart","source":"startup"}' off)"
started="$(standards '{"hook_event_name":"SessionStart","source":"startup"}')"
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
worst="$(context_of "$(standards '{"hook_event_name":"SessionStart","source":"startup"}' on "$long_root")")"
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
  printf '{"hook_event_name":"SessionStart","source":"compact","cwd":"%s"}' "$1" | CLAUDE_PLUGIN_ROOT="$plugin" CLAUDE_PROJECT_DIR="$work/parent" CLAUDE_PLUGIN_DATA="$work/data" bash "$plugin/hooks/context.sh" unity-dev
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
ALL="locomotion crowd balance ui scene-cost colliders off-screen budgets inspect_animation inspect_character study validate_mesh"

printf 'class A {}\n' > "$project/Assets/A.cs"
result="$(gates_from_cwd)"
check "C# without a receipt: valid JSON that blocks, from a session started above" "block" "$(printf '%s' "$result" | json_field "d['decision']")"
check "C# without a receipt: names architecture" "architecture" "$result"
absent "a line of C# doesn't ask for a balance simulation" "balance" "$result"
absent "or for a walk test" "locomotion" "$result"
printf 'class EnemyFactory {}\n' > "$project/Assets/EnemyFactory.cs"
sleep 1
absent "a factory isn't an actor" "locomotion" "$(gates '{}')"
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
printf 'class HudView {}\n' > "$project/Assets/UI/HudView.cs"
check "waivers of what the change touches are asked about again" "is that still true? ui" "$(gates '{}')"
sleep 1
receipt architecture.txt
gates '{}' > /dev/null
sleep 1
receipt architecture.txt
printf 'x\n' >> "$project/README.md"
empty "with a newer passing receipt, nothing to say" "$(gates '{}')"

newer "Assets/A.cs"
receipt architecture.txt false
result="$(gates '{"session_id":"one"}')"
check "a failing receipt is named" "Failing: architecture.txt" "$result"
check "it asks for plain words" "what the player would see" "$result"
newer "Assets/A.cs"
empty "the same failure isn't told twice in a session" "$(gates '{"session_id":"one"}')"
newer "Assets/A.cs"
check "a new session is told again" "Failing: architecture.txt" "$(gates '{"session_id":"two"}')"
printf 'passed: false\nissues: other\n' > "$project/docs/proofs/architecture.txt"
sleep 1
newer "Assets/A.cs"
check "a failure that changed is told again" "Failing: architecture.txt" "$(gates '{"session_id":"two"}')"
printf 'architecture: the user said to leave it for now\n' >> "$project/docs/proofs/not-applicable.txt"
sleep 1
receipt architecture.txt false
printf 'x\n' >> "$project/README.md"
empty "a failure the user accepted, with the receipt current, says nothing" "$(gates '{"session_id":"three"}')"
newer "Assets/A.cs"
result="$(gates '{"session_id":"three"}')"
check "an accepted failure older than the change is asked about" "Older than what changed: architecture.txt" "$result"
check "and whether it still holds" "is that still true? architecture" "$result"
waive $ALL
for k in 1 2 3 4 5 6 7; do printf 'passed: false\n' > "$project/docs/proofs/balance-$k.txt"; done
mkdir -p "$project/Assets/Economy"
printf 'class Prices {}\n' > "$project/Assets/Economy/Prices.cs"
check "many failures: the first names and a count" "and 3 more" "$(gates '{"session_id":"four"}')"
rm "$project/docs/proofs/"balance-*.txt
receipt architecture.txt
gates '{}' > /dev/null

newer "Assets/A.cs"
empty "a continuation never blocks" "$(gates '{"stop_hook_active":true}')"
receipt architecture.txt
gates '{}' > /dev/null

receipt balance-casual.txt
newer "Assets/A.cs"
result="$(gates '{}')"
check "C# elsewhere makes the architecture receipt old" "architecture.txt" "$result"
absent "and leaves the balance receipt alone" "balance-casual.txt" "$result"
receipt architecture.txt
gates '{}' > /dev/null
mkdir -p "$project/Assets/Economy"
printf 'class PriceList {}\n' > "$project/Assets/Economy/PriceList.cs"
check "C# of its own area makes a balance receipt old" "balance-casual.txt" "$(gates '{}')"
receipt architecture.txt
receipt balance-casual.txt
gates '{}' > /dev/null

printf 'text\n' >> "$project/README.md"
empty "docs alone ask for nothing" "$(gates '{}')"

waive locomotion crowd balance scene-cost colliders off-screen budgets inspect_animation inspect_character study validate_mesh
printf 'x\n' > "$project/Assets/UI/Hud.uxml"
check "UI Toolkit files need a UI receipt" "ui" "$(gates '{}')"
receipt ui-hud.txt
gates '{}' > /dev/null

waive locomotion crowd balance scene-cost colliders off-screen budgets inspect_animation inspect_character study
printf 'x\n' > "$project/Assets/Art/rock.png"
empty "a texture asks for nothing" "$(gates '{}')"
printf 'x\n' > "$project/Assets/Art/hero.fbx"
git -C "$project" add -A
git -C "$project" -c user.name=t -c user.email=t@t commit -q -m art
check "a commit since the last check still counts" "validate_mesh" "$(gates '{}')"
receipt validate_mesh-hero.json
gates '{}' > /dev/null

# One model changed: its receipts, not those of the other models.
receipt validate_mesh-rock.json
sleep 1
newer "Assets/Art/hero.fbx"
result="$(gates '{}')"
check "a changed model's own receipt is old" "validate_mesh-hero.json" "$result"
absent "another model's isn't" "validate_mesh-rock.json" "$result"
receipt validate_mesh-hero.json
gates '{}' > /dev/null
printf 'x\n' > "$project/Assets/Art/barrel.fbx"
check "a new model with no receipt of its own" "validate_mesh" "$(gates '{}')"
receipt validate_mesh-barrel.json
gates '{}' > /dev/null
printf '{\n "passed": true\n}\n' > "$project/docs/proofs/inspect_character-hero.json"
sleep 1
newer "Assets/Art/hero.fbx"
check "a model with a character receipt answers for it, wherever it sits" "inspect_character-hero.json" "$(gates '{}')"
receipt validate_mesh-hero.json
printf '{\n "passed": true\n}\n' > "$project/docs/proofs/inspect_character-hero.json"
sleep 1
gates '{}' > /dev/null
newer "Assets/Art/barrel.fbx"
absent "a prop doesn't ask for a character check" "inspect_character" "$(gates '{}')"
receipt validate_mesh-barrel.json
gates '{}' > /dev/null
rm "$project/docs/proofs/validate_mesh-rock.json" "$project/docs/proofs/validate_mesh-barrel.json" "$project/docs/proofs/inspect_character-hero.json"

mkdir -p "$project/Tools"
printf 'x\n' > "$project/Tools/build_art.py"
check "tools that produce assets count too" "Older than what changed: validate_mesh-hero.json" "$(gates '{}')"
receipt validate_mesh-hero.json
printf '{\n "passed": false\n}\n' > "$project/docs/proofs/inspect_character-hero.json"
sleep 1
newer "Assets/Art/hero.fbx"
check "a failing Blender receipt is named" "Failing: inspect_character-hero.json" "$(gates '{}')"
rm "$project/docs/proofs/inspect_character-hero.json"
printf '{\n "passed": true\n}\n' > "$project/docs/proofs/inspect_character-hero-parts.json"
printf '{\n "passed": true\n}\n' > "$project/docs/proofs/inspect_character-hero.json"
receipt validate_mesh-hero.json
sleep 1
newer "Tools/build_art.py"
result="$(gates '{}')"
case "$result" in
  *inspect_character-hero-parts*) echo "FAIL a whole-parts receipt comes before the cut, and isn't old for that: $result"; failed=1 ;;
  *) echo "ok   a whole-parts receipt comes before the cut, and isn't old for that" ;;
esac
check "the final receipt still is" "inspect_character-hero.json" "$result"
rm "$project/docs/proofs/inspect_character-hero.json" "$project/docs/proofs/inspect_character-hero-parts.json"

receipt validate_mesh-hero.json
gates '{}' > /dev/null
printf 'x\n' > "$project/Assets/Art/hero.fbx.meta"
empty "Unity writing a .meta on import asks for nothing" "$(gates '{}')"

waive locomotion crowd balance scene-cost colliders off-screen budgets inspect_character study
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

# A game built in one long turn answers for every proof.
big="$work/big"
mkdir -p "$big/ProjectSettings" "$big/Assets/_Project/Scripts" "$big/.claude" "$big/docs/proofs"
echo "m_EditorVersion: 6000.6.2f1" > "$big/ProjectSettings/ProjectVersion.txt"
i=0
while [ $i -lt 35 ]; do printf 'class B%s {}\n' "$i" > "$big/Assets/_Project/Scripts/B$i.cs"; i=$((i + 1)); done
git -C "$big" init -q
result="$(gates '{}' on "$big")"
check "many files and no proofs: all of them are missing" "locomotion" "$result"
check "balance too" "balance" "$result"
check "and art" "validate_mesh" "$result"
for family in architecture locomotion crowd balance ui scene-cost colliders off-screen budgets inspect_animation inspect_character study validate_mesh; do
  printf 'passed: true\n' > "$big/docs/proofs/$family-all.txt"
done
sleep 1
printf 'class B0 { int a; }\n' > "$big/Assets/_Project/Scripts/B0.cs"
result="$(gates '{}' on "$big")"
check "one more change: its own check" "architecture-all.txt" "$result"
absent "and no other" "balance-all.txt" "$result"
for family in architecture; do printf 'passed: true\n' > "$big/docs/proofs/$family-all.txt"; done
sleep 1
i=0
while [ $i -lt 35 ]; do printf 'class B%s { int b; }\n' "$i" > "$big/Assets/_Project/Scripts/B$i.cs"; i=$((i + 1)); done
check "many changes since a proof make it old" "balance-all.txt" "$(gates '{}' on "$big")"

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
sleep 1
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

# What a review of the hook found.
quick="$work/quick"
mkdir -p "$quick/ProjectSettings" "$quick/Assets/_Project/Art" "$quick/Assets/_Project/Scripts/Library" "$quick/Assets/Store" "$quick/docs/proofs"
echo "m_EditorVersion: 6000.6.2f1" > "$quick/ProjectSettings/ProjectVersion.txt"
git -C "$quick" init -q
printf 'x\n' > "$quick/ProjectSettings/x"
git -C "$quick" add -A
git -C "$quick" -c user.name=t -c user.email=t@t commit -q -m first
gates '{}' on "$quick" > /dev/null
sleep 1
qreceipt() { printf '%s\n' "${2:-passed: true}" > "$quick/docs/proofs/$1"; sleep 1; }
printf 'class C {}\n' > "$quick/Assets/_Project/Scripts/Library/C.cs"
check "a folder of ours named Library counts" "architecture" "$(gates '{}' on "$quick")"
qreceipt architecture.txt
gates '{}' on "$quick" > /dev/null
printf '{"references":[]}\n' > "$quick/Assets/_Project/Scripts/Game.asmdef"
check "an assembly definition asks for the architecture check" "architecture" "$(gates '{}' on "$quick")"
qreceipt architecture.txt
git -C "$quick" add -A
git -C "$quick" -c user.name=t -c user.email=t@t commit -q -m code
gates '{}' on "$quick" > /dev/null
sleep 1
qreceipt architecture.txt
sleep 1
rm "$quick/Assets/_Project/Scripts/Library/C.cs"
check "a C# file deleted after the check" "architecture.txt" "$(gates '{}' on "$quick")"
qreceipt architecture.txt
git -C "$quick" add -A
git -C "$quick" -c user.name=t -c user.email=t@t commit -q -m gone
gates '{}' on "$quick" > /dev/null
sleep 1
printf 'x\n' >> "$quick/README.md"
empty "a bare commit and a document ask for nothing" "$(git -C "$quick" add -A; git -C "$quick" -c user.name=t -c user.email=t@t commit -q -m doc; gates '{}' on "$quick")"
for k in 1 2 3; do printf 'x\n' > "$quick/Assets/_Project/Art/model$k.fbx"; done
sleep 1
qreceipt validate_mesh-model1.json
result="$(gates '{}' on "$quick")"
check "a model with no receipt of its own, beside one with" "validate_mesh:model2" "$result"
absent "the one with a receipt isn't named" "validate_mesh:model1" "$result"
for k in 2 3; do qreceipt validate_mesh-model$k.json; done
printf '{\n "passed": false\n}\n' > "$quick/docs/proofs/validate_mesh-rock.json"
sleep 1
gates '{}' on "$quick" > /dev/null
printf 'y\n' >> "$quick/Assets/_Project/Art/model1.fbx"
result="$(gates '{}' on "$quick")"
absent "another model's failure isn't this model's" "validate_mesh-rock" "$result"
check "this model's receipt is old" "validate_mesh-model1.json" "$result"
qreceipt validate_mesh-model1.json
printf 'x\n' > "$quick/Assets/_Project/Art/Cliff_1.fbx"
qreceipt validate_mesh-Cliff_10.json
check "Cliff_10's receipt isn't Cliff_1's" "validate_mesh:Cliff_1" "$(gates '{}' on "$quick")"
qreceipt validate_mesh-Cliff_1.json
gates '{}' on "$quick" > /dev/null
printf 'x\n' > "$quick/Assets/Store/Tree.fbx"
empty "a model of a store pack isn't this project's to check" "$(gates '{}' on "$quick")"
printf 'head LimbNode tail\n' > "$quick/Assets/_Project/Art/Knight.fbx"
sleep 1
qreceipt validate_mesh-Knight.json
check "a rig in the file makes it a character, whatever its name" "inspect_character:Knight" "$(gates '{}' on "$quick")"
printf '{\n "passed": true\n}\n' > "$quick/docs/proofs/inspect_character-Knight.json"
sleep 1
gates '{}' on "$quick" > /dev/null
printf 'ui: no UI yet\n' > "$quick/docs/proofs/not-applicable.txt"
sleep 1
printf 'x\n' > "$quick/Assets/_Project/Hud.uxml"
check "the first file of what was \"not yet\" asks about it" "is that still true? ui" "$(gates '{"session_id":"w"}' on "$quick")"
sleep 1
printf 'y\n' >> "$quick/Assets/_Project/Hud.uxml"
empty "and only once in a session" "$(gates '{"session_id":"w"}' on "$quick")"
printf 'passed: false\n' > "$quick/docs/proofs/architecture-we\"ird.txt"
sleep 1
printf 'class D {}\n' > "$quick/Assets/_Project/Scripts/D.cs"
result="$(gates '{"session_id":"w"}' on "$quick")"
check "a quote in a receipt's name still gives valid JSON" "block" "$(printf '%s' "$result" | json_field "d['decision']")"
rm "$quick/docs/proofs/architecture-we\"ird.txt"

# Many models with many receipts, inside the timeout.
crowd="$work/crowd"
mkdir -p "$crowd/ProjectSettings" "$crowd/Assets/_Project/Art" "$crowd/docs/proofs"
echo "m_EditorVersion: 6000.6.2f1" > "$crowd/ProjectSettings/ProjectVersion.txt"
git -C "$crowd" init -q
i=0
while [ $i -lt 73 ]; do
  printf 'x\n' > "$crowd/Assets/_Project/Art/Model$i.fbx"
  printf 'x\n' > "$crowd/Assets/_Project/Art/Model$i.fbx.meta"
  i=$((i + 1))
done
sleep 1
i=0
while [ $i -lt 73 ]; do
  printf 'passed: true\n' > "$crowd/docs/proofs/validate_mesh-Model$i.txt"
  printf 'passed: true\n' > "$crowd/docs/proofs/inspect_character-Model$i.txt"
  i=$((i + 1))
done
started=$(date +%s)
gates '{}' on "$crowd" > /dev/null
seconds=$(( $(date +%s) - started ))
if [ "$seconds" -lt 15 ]; then echo "ok   73 models with their receipts took $seconds s"; else echo "FAIL 73 models with their receipts took $seconds s"; failed=1; fi

# Receipts are written by the checks.
edit_hook() { # path
  printf '{"tool_name":"Write","tool_input":{"file_path":"%s"},"cwd":"%s"}' "$1" "$project" | CLAUDE_PLUGIN_ROOT="$plugins/core" bash "$plugins/core/hooks/receipts.sh"
}
check "writing a receipt by hand is refused" "deny" "$(edit_hook "$project/docs/proofs/architecture.txt" | json_field "d['hookSpecificOutput']['permissionDecision']")"
empty "the list of what doesn't apply can be edited" "$(edit_hook "$project/docs/proofs/not-applicable.txt")"
empty "any other file costs nothing" "$(edit_hook "$project/Assets/A.cs")"


# --- Domains: switches, what each brings, and when a domain's standards reach the session ---

if python3 "$root/dev/sync.py" --check > /dev/null; then echo "ok   the plugins' shared hooks and tables are in sync"; else echo "FAIL dev/sync.py --check: run python3 dev/sync.py"; failed=1; fi

proj="$work/domains"
mkdir -p "$proj/.claude"
mkdir -p "$work/home"
ctx() { # plugin, input, folder; a home of its own, so the user's own settings don't decide the tests
  printf '%s' "$2" | HOME="$work/home" CLAUDE_PLUGIN_ROOT="$plugins/$1" CLAUDE_PROJECT_DIR="$3" CLAUDE_PLUGIN_DATA="$work/data-$1" bash "$plugins/$1/hooks/context.sh" "$1"
}
session_start() { # plugin, session
  ctx "$1" "{\"hook_event_name\":\"SessionStart\",\"source\":\"compact\",\"session_id\":\"$2\",\"cwd\":\"$proj\"}" "$proj"
}
prompt() { # plugin, session, prompt as it appears in JSON
  ctx "$1" "{\"hook_event_name\":\"UserPromptSubmit\",\"session_id\":\"$2\",\"cwd\":\"$proj\",\"prompt\":\"$3\"}" "$proj"
}
subagent() { # plugin, session, agent type
  ctx "$1" "{\"hook_event_name\":\"SubagentStart\",\"session_id\":\"$2\",\"agent_type\":\"${3:-general-purpose}\",\"cwd\":\"$proj\"}" "$proj"
}
switches() { # the env object's content
  printf '{"env":{%s}}\n' "$1" > "$proj/.claude/settings.json"
}

switches ''
for domain in core game-design modeling unity-dev; do empty "$domain: nothing on, nothing loads" "$(session_start "$domain" s0)"; done

switches '"UNITY_DEV_STANDARDS":"on"'
for domain in core game-design modeling unity-dev; do check "$domain comes on with unity-dev" "SessionStart" "$(session_start "$domain" s1)"; done
check "core names what the project has on" "Switched on in this project: core; game-design; modeling; unity-dev" "$(session_start core s1 | json_field "d['systemMessage']")"
empty "only core names it" "$(session_start modeling s1 | json_field "d.get('systemMessage','')")"

message="$(session_start core s1 | json_field "d['systemMessage']")"
check "core names the domains without a read rule" "No read rule for: core, game-design, modeling, unity-dev" "$message"
printf '{"env":{"UNITY_DEV_STANDARDS":"on"},"permissions":{"allow":["Read(~/.claude/plugins/cache/*/unity-dev/**)"]}}\n' > "$proj/.claude/settings.json"
check "a project set up before the split lacks the new domains' rules" "No read rule for: core, game-design, modeling" "$(session_start core s1 | json_field "d['systemMessage']")"
check "and the session is told to say so once" "tell the user once" "$(context_of "$(session_start core s1)")"
printf '{"env":{"UNITY_DEV_STANDARDS":"on"},"permissions":{"allow":["Read(~/.claude/plugins/cache/*/unity-dev/**)","Read(~/.claude/plugins/cache/*/core/**)","Read(~/.claude/plugins/cache/*/game-design/**)","Read(~/.claude/plugins/cache/*/modeling/**)"]}}\n' > "$proj/.claude/settings.json"
absent "with every rule, nothing about them" "No read rule" "$(session_start core s1 | json_field "d['systemMessage']")"

switches '"UNITY_DEV_STANDARDS":"on","MODELING_STANDARDS":"off"'
empty "a domain switched off stays off" "$(session_start modeling s2)"
check "the others stay on" "SessionStart" "$(session_start game-design s2)"
check "and core says so" "Switched on in this project: core; game-design; unity-dev" "$(session_start core s2 | json_field "d['systemMessage']")"

switches '"UNITY_DEV_STANDARDS":"on","UNITY_DEV_SKILL_VFX":"off"'
context="$(context_of "$(session_start unity-dev s3)")"
absent "a skill switched off loses its row" "../vfx/SKILL.md" "$context"
check "and the session is told" "so their rows are left out: vfx" "$context"
check "the other rows stay" "../audio-design/SKILL.md" "$context"
check "a must of a skill that is on stays" "ProjectArchitectureTests" "$context"

switches '"UNITY_DEV_STANDARDS":"on","UNITY_DEV_SKILL_CODE_STANDARDS":"off"'
absent "a must of a skill switched off goes with it" "ProjectArchitectureTests" "$(context_of "$(session_start unity-dev s3b)")"

switches '"MODELING_SKILL_CHARACTERS":"on"'
context="$(context_of "$(session_start modeling s4)")"
check "one skill on alone: its row" "| [characters](../characters/SKILL.md)" "$context"
absent "and not the others" "| [animation](../animation/SKILL.md)" "$context"
check "it brings core" "SessionStart" "$(session_start core s4)"
empty "not unity-dev" "$(session_start unity-dev s4)"
empty "nor game-design" "$(session_start game-design s4)"

switches '"UNITY_DEV_SKILL_VFX":"on"'
check "one unity-dev skill on alone brings core" "SessionStart" "$(session_start core s4b)"
empty "but not game-design" "$(session_start game-design s4b)"
empty "nor modeling" "$(session_start modeling s4b)"
check "and its own row" "../vfx/SKILL.md" "$(context_of "$(session_start unity-dev s4b)")"

switches '"UNITY_DEV_STANDARDS":"on","CORE_STANDARDS":"off"'
check "core can't be switched off while a domain is on" "SessionStart" "$(session_start core s4c)"
switches '"UNITY_DEV_STANDARDS":"on","CORE_SKILL_PROJECT_DOCS":"off","CORE_SKILL_SKILLS":"off","CORE_SKILL_VERSION_NOTES":"off"'
context="$(context_of "$(session_start core s4d)")"
check "with all its guides off, core still gives its standards" "How the work runs" "$context"
absent "without their rows" "../project-docs/SKILL.md" "$context"
switches '"CORE_STANDARDS":"off"'
empty "core switched off with nothing else on: nothing" "$(session_start core s4e)"

switches '"UNITY_DEV_STANDARDS":"on"'
printf '{"env":{"GAME_DESIGN_STANDARDS":"off"}}\n' > "$proj/.claude/settings.local.json"
empty "the personal file wins" "$(session_start game-design s5)"
check "for its own key only" "SessionStart" "$(session_start unity-dev s5)"
rm "$proj/.claude/settings.local.json"
empty "the session's variable wins over the files" "$(MODELING_STANDARDS=off session_start modeling s5)"

for domain in core game-design modeling unity-dev; do
  size="$(context_of "$(session_start "$domain" "size-$domain")" | wc -m | tr -d ' ')"
  if [ "$size" -lt 9500 ]; then echo "ok   $domain's standards are $size characters"; else echo "FAIL $domain's standards are $size characters, too close to the 10,000 cap"; failed=1; fi
done

# A standards command brings what its domain builds on in the same turn; the command itself brings its own.
switches ''
check "a standards command pulls in core" 'typed `/modeling:standards`' "$(context_of "$(prompt core p1 '/modeling:standards make a chair')")"
empty "not its own domain: the command gives it" "$(prompt modeling p1 '/modeling:standards make a chair')"
empty "nor domains it doesn't build on" "$(prompt unity-dev p1 '/modeling:standards make a chair')"
empty "nor twice in a session" "$(prompt core p1 'go on')"
empty "and the command's own domain isn't added later" "$(prompt modeling p1 'go on')"
check "unity-dev's pulls modeling" "UserPromptSubmit" "$(prompt modeling p2 '/unity-dev:standards build a level')"
check "and game-design" "UserPromptSubmit" "$(prompt game-design p2 '/unity-dev:standards build a level')"
empty "another skill's command pulls nothing" "$(prompt core p3 '/unity-dev:vfx sparks')"
empty "nor a mention in plain words" "$(prompt core p3 'use /unity-dev:standards later')"
check "a command followed by a new line" "UserPromptSubmit" "$(prompt core p4 '/game-design:standards\nan idle game')"
switches '"MODELING_STANDARDS":"off"'
empty "a domain switched off isn't pulled" "$(prompt modeling p5 '/unity-dev:standards build a level')"
switches '"GAME_DESIGN_SKILL_ART_DIRECTION":"off"'
context="$(context_of "$(prompt game-design p6 '/unity-dev:standards build a level')")"
check "a pulled domain keeps the skills that are on" "../game-design/SKILL.md" "$context"
absent "and leaves out one switched off" "../art-direction/SKILL.md" "$context"

switches ''
empty "\`/unity-dev:standards off\` pulls nothing" "$(prompt core p7 '/unity-dev:standards off')"
empty "nor \`on\`" "$(prompt core p8 '/unity-dev:standards on')"
check "a word after on is a task" "UserPromptSubmit" "$(prompt core p9 '/unity-dev:standards on second thought, build it')"

# What a command brought comes back after compaction; a session resumed from its transcript gets nothing twice.
prompt game-design p10 '/unity-dev:standards build a level' > /dev/null
prompt unity-dev p10 '/unity-dev:standards build a level' > /dev/null
started_as() { # plugin, source, session
  ctx "$1" "{\"hook_event_name\":\"SessionStart\",\"source\":\"$2\",\"session_id\":\"$3\",\"cwd\":\"$proj\"}" "$proj"
}
compacted() { # plugin, session
  started_as "$1" compact "$2"
}
check "a pulled domain is given again after compaction" "load here again" "$(context_of "$(compacted game-design p10)")"
check "and the command's own domain too" "load here again" "$(context_of "$(compacted unity-dev p10)")"
empty "a session that never had it gets nothing" "$(compacted game-design p11)"
switches '"MODELING_STANDARDS":"on"'
empty "a resumed session gets nothing at its start" "$(started_as modeling resume r1)"
empty "nor at its next prompt: its transcript has them" "$(prompt modeling r1 'go on')"
switches ''

# Without a data folder of their own, the plugins don't share their notes of what a session has.
shared_tmp="$work/shared-tmp"
mkdir -p "$shared_tmp"
no_data() { # plugin, session, prompt
  printf '{"hook_event_name":"UserPromptSubmit","session_id":"%s","cwd":"%s","prompt":"%s"}' "$2" "$proj" "$3" | env -u CLAUDE_PLUGIN_DATA TMPDIR="$shared_tmp" HOME="$work/home" CLAUDE_PLUGIN_ROOT="$plugins/$1" CLAUDE_PROJECT_DIR="$proj" bash "$plugins/$1/hooks/context.sh" "$1"
}
no_data unity-dev n1 '/unity-dev:standards build' > /dev/null
check "one plugin's note doesn't silence another's" "UserPromptSubmit" "$(no_data core n1 '/unity-dev:standards build')"

# A byte that isn't UTF-8 leaves the rest of the text whole.
escaped="$(printf 'abc\351def' | LC_ALL=en_US.UTF-8 bash -c ". '$plugins/core/hooks/lib.sh'; json_escape")"
check "json_escape keeps what follows a byte that isn't UTF-8" "def" "$escaped"

# A domain turned on during a session loads with the next prompt, once.
switches ''
empty "before the switch" "$(prompt modeling t1 'hello')"
switches '"MODELING_STANDARDS":"on"'
check "the next prompt after it loads the domain" "turned on in this project during this session" "$(context_of "$(prompt modeling t1 'hello again')")"
empty "once" "$(prompt modeling t1 'and again')"
session_start modeling t2 > /dev/null
empty "a session that started with it doesn't get it twice" "$(prompt modeling t2 'hi')"

# Subagents.
check "a subagent gets the domains that are on" "You are a subagent" "$(context_of "$(subagent modeling t2)")"
empty "a read-only one doesn't" "$(subagent modeling t2 Explore)"
switches ''
check "a subagent of a session a command gave a domain gets it too" "SubagentStart" "$(subagent core p1)"
empty "a subagent of a session without it doesn't" "$(subagent core nobody)"

# Receipts are protected wherever any domain is on.
receipt_edit() { # folder
  printf '{"tool_name":"Edit","tool_input":{"file_path":"%s/docs/proofs/validate_mesh-Chair.json"},"cwd":"%s"}' "$1" "$1" | CLAUDE_PLUGIN_ROOT="$plugins/core" bash "$plugins/core/hooks/receipts.sh"
}
switches ''
empty "receipts in a project with nothing on are left alone" "$(receipt_edit "$proj")"
content_edit() { # file path, content
  printf '{"tool_name":"Write","tool_input":{"file_path":"%s","content":"%s"},"cwd":"%s"}' "$1" "$2" "$proj" | HOME="$work/home" CLAUDE_PLUGIN_ROOT="$plugins/core" bash "$plugins/core/hooks/receipts.sh"
}
switches '"UNITY_DEV_STANDARDS":"on"'
empty "a file that mentions docs/proofs/ in its content is no receipt" "$(content_edit "$proj/CLAUDE.md" 'Receipts live in docs/proofs/.')"
check "a receipt whose content names not-applicable.txt is still a receipt" "deny" "$(content_edit "$proj/docs/proofs/architecture.txt" 'see docs/proofs/not-applicable.txt')"
empty "not-applicable.txt itself can be written" "$(content_edit "$proj/docs/proofs/not-applicable.txt" 'ui: no UI yet')"
switches '"UNITY_DEV_STANDARDS":"on","CORE_STANDARDS":"off"'
check "receipts stay protected with core switched off" "deny" "$(receipt_edit "$proj")"
switches '"MODELING_STANDARDS":"on"'
check "with modeling on, a hand edit of a receipt is refused" "deny" "$(receipt_edit "$proj")"

# The Stop hook asks only for the receipts of skills that are on.
families="$work/families"
mkdir -p "$families/ProjectSettings" "$families/Assets/_Project/Art" "$families/docs/proofs" "$families/.claude"
echo "m_EditorVersion: 6000.6.2f1" > "$families/ProjectSettings/ProjectVersion.txt"
git -C "$families" init -q
family_gate() { # env object content
  printf '{"env":{%s}}\n' "$1" > "$families/.claude/settings.json"
  printf '{"cwd":"%s","session_id":"f%s"}' "$families" "$RANDOM" | CLAUDE_PLUGIN_ROOT="$plugin" CLAUDE_PROJECT_DIR="$families" CLAUDE_PLUGIN_DATA="$work/data-families-$RANDOM" bash "$plugin/hooks/gates.sh"
}
printf 'x\n' > "$families/Assets/_Project/Art/Chair.fbx"
check "a model asks for its mesh check with modeling on" "validate_mesh" "$(family_gate '"UNITY_DEV_STANDARDS":"on"')"
absent "and not with modeling off" "validate_mesh" "$(family_gate '"UNITY_DEV_STANDARDS":"on","MODELING_STANDARDS":"off"')"
absent "nor with modeling's models and characters off" "validate_mesh" "$(family_gate '"UNITY_DEV_STANDARDS":"on","MODELING_SKILL_MODELS":"off","MODELING_SKILL_CHARACTERS":"off"')"
check "characters on keep the mesh check of their models" "validate_mesh" "$(family_gate '"UNITY_DEV_STANDARDS":"on","MODELING_SKILL_MODELS":"off"')"
empty "and the gate is off without unity-dev" "$(family_gate '"MODELING_STANDARDS":"on"')"

[ "$failed" = 0 ] && echo "all hook tests passed"
exit "$failed"
