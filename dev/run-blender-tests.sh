#!/usr/bin/env bash
# Runs the Blender scripts headless against test scenes with known results (dev/blender/): modeling's scripts/ and
# game-design's study_screenshot.py.
# Usage: dev/run-blender-tests.sh [path-to-blender]
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
scripts="$root/plugins/modeling/scripts"
study="$root/plugins/game-design/skills/art-direction/scripts"
blender="${1:-blender}"
out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT

echo "$("$blender" --version | head -n 1)"
status=0
for test in validate_mesh render_views inspect_character inspect_animation export_fbx build_body study_screenshot bake_light; do
  script="$scripts/$test.py"
  [ "$test" = study_screenshot ] && script="$study/$test.py"
  if "$blender" -b --factory-startup --python-exit-code 1 --python "$root/dev/blender/test_$test.py" -- "$script" "$out" > "$out/$test.log" 2>&1; then
    echo "$test: passed"
  else
    echo "$test: failed"
    grep -E 'CASE FAIL|AssertionError|Traceback|Error' "$out/$test.log" | head -n 20 || true
    status=1
  fi
done
exit $status
