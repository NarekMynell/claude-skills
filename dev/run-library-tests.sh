#!/usr/bin/env bash
# Copies the code library into the test project and runs its Edit Mode and Play Mode tests headless.
# Usage: dev/run-library-tests.sh [path-to-Unity-binary]
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
project="$root/dev/library-tests"
library="$root/plugins/unity-dev/skills/library/code"
unity="${1:-/Applications/Unity/Hub/Editor/$(sed -n 's/^m_EditorVersion: *//p' "$project/ProjectSettings/ProjectVersion.txt")/Unity.app/Contents/MacOS/Unity}"

mkdir -p "$project/Assets/_Project/Scripts"
rsync -a --delete --exclude '*.meta' "$library/" "$project/Assets/_Project/Scripts/"

# A run that hangs (for example a Play Mode run stuck in the wrong scene) fails instead of blocking forever.
timeout_seconds=900

status=0
for platform in EditMode PlayMode; do
  results="$project/Logs/results-$platform.xml"
  rm -f "$results"
  perl -e 'alarm shift; exec @ARGV' "$timeout_seconds" "$unity" -batchmode -projectPath "$project" -runTests -testPlatform "$platform" \
    -testResults "$results" -logFile "$project/Logs/tests-$platform.log" || status=1
  if [ -f "$results" ]; then
    summary="$(grep -m1 '<test-run' "$results" | sed -E 's/.*total="([0-9]+)".*passed="([0-9]+)".*failed="([0-9]+)".*skipped="([0-9]+)".*/total \1, passed \2, failed \3, skipped \4/')"
    echo "$platform: $summary"
  else
    echo "$platform: no results (compile error?) - see Logs/tests-$platform.log"
    grep -E "error CS|Exception" "$project/Logs/tests-$platform.log" | head -n 20 || true
    status=1
  fi
done
exit $status
