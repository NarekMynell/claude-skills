#!/usr/bin/env bash
# Copies the code library into the test project and runs its tests headless.
# Usage: dev/run-library-tests.sh [player [BuildTarget]] [path-to-Unity-binary]
#   no mode: Edit Mode and Play Mode tests in the Editor.
#   player:  the Play Mode tests in a development player, by default for this machine's desktop platform
#            (WebGL opens the default browser). It builds from a temporary copy of the project whose build list
#            also holds the test scenes, which Editor runs keep out of it to cover the Editor-only scene loading.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
project="$root/dev/library-tests"
library="$root/plugins/unity-dev/skills/library/code"

mode=editor
target=""
if [ "${1:-}" = "player" ]; then
  mode=player
  shift
  case "${1:-}" in
    Standalone*|WebGL|Android|iOS) target="$1"; shift ;;
  esac
  if [ -z "$target" ]; then
    case "$(uname -s)" in
      Darwin) target=StandaloneOSX ;;
      Linux) target=StandaloneLinux64 ;;
      *) target=StandaloneWindows64 ;;
    esac
  fi
fi

unity="${1:-/Applications/Unity/Hub/Editor/$(sed -n 's/^m_EditorVersion: *//p' "$project/ProjectSettings/ProjectVersion.txt")/Unity.app/Contents/MacOS/Unity}"

mkdir -p "$project/Assets/_Project/Scripts" "$project/Logs"
rsync -a --delete --exclude '*.meta' "$library/" "$project/Assets/_Project/Scripts/"

# A run that hangs (for example a Play Mode run stuck in the wrong scene) fails instead of blocking forever.
# Player runs include a build, which takes much longer for WebGL.
timeout_seconds=900
if [ "$mode" = player ]; then timeout_seconds=2700; fi

status=0

# Runs one test platform and prints its summary. Arguments: project, test platform, result name, extra Unity arguments.
run() {
  local run_project="$1" platform="$2" name="$3"
  shift 3
  local results="$project/Logs/results-$name.xml"
  rm -f "$results"
  perl -e 'alarm shift; exec @ARGV' "$timeout_seconds" "$unity" -batchmode -projectPath "$run_project" "$@" -runTests -testPlatform "$platform" \
    -testResults "$results" -logFile "$project/Logs/tests-$name.log" || status=1
  if [ -f "$results" ]; then
    summary="$(grep -m1 '<test-run' "$results" | sed -E 's/.*total="([0-9]+)".*passed="([0-9]+)".*failed="([0-9]+)".*skipped="([0-9]+)".*/total \1, passed \2, failed \3, skipped \4/')"
    echo "$name: $summary"
  else
    echo "$name: no results (compile error?) - see Logs/tests-$name.log"
    grep -E "error CS|Exception" "$project/Logs/tests-$name.log" | head -n 20 || true
    status=1
  fi
}

if [ "$mode" = editor ]; then
  for platform in EditMode PlayMode; do
    run "$project" "$platform" "$platform"
  done
  exit $status
fi

work_root="$(mktemp -d)"
trap 'rm -rf "$work_root"' EXIT
work="$work_root/library-tests"
rsync -a --exclude Logs --exclude Temp "$project/" "$work/"

# Adds every test scene that isn't in the build list yet, before the list's closing key.
settings="$work/ProjectSettings/EditorBuildSettings.asset"
entries=""
for scene in "$work"/Assets/LibraryTests/Scenes/*.unity; do
  path="${scene#$work/}"
  grep -q "path: $path\$" "$settings" && continue
  guid="$(sed -n 's/^guid: *//p' "$scene.meta")"
  entries="$entries  - enabled: 1\n    path: $path\n    guid: $guid\n"
done
awk -v add="$entries" '/^  m_configObjects:/ { printf "%s", add } { print }' "$settings" > "$settings.tmp"
mv "$settings.tmp" "$settings"

run "$work" "$target" "player-$target" -buildTarget "$target"
exit $status
