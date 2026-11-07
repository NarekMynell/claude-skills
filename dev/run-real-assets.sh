#!/usr/bin/env bash
# Runs the Blender checks over the professional models and clips inside a Unity install, and compares what they say with
# dev/blender/real_assets_expected.txt. A check gets its clean cases from work it didn't help build: this is what the test scenes can't
# show. A line that differs is either a check that got worse, or one that got better: read it, and update the list with the reason.
# Usage: dev/run-real-assets.sh [path-to-blender] [path-to-BuiltInPackages]
set -uo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
blender="${1:-blender}"
version="$(sed -n 's/^m_EditorVersion: *//p' "$root/dev/library-tests/ProjectSettings/ProjectVersion.txt")"
packages="${2:-/Applications/Unity/Hub/Editor/$version/Unity.app/Contents/Resources/PackageManager/BuiltInPackages}"
if [ ! -d "$packages" ]; then
  echo "no Unity packages at $packages: pass the folder as the second argument"
  exit 0
fi
expected="$root/dev/blender/real_assets_expected.txt"
out="$(mktemp)"
trap 'rm -f "$out"' EXIT
"$blender" -b --factory-startup --python "$root/dev/blender/real_assets.py" -- "$root" "$packages" > "$out" 2>&1
found="$(grep '^REAL	' "$out" | cut -f 2- | LC_ALL=C sort)"
if [ -z "$found" ]; then
  echo "nothing ran:"
  tail -n 20 "$out"
  exit 1
fi
total="$(printf '%s\n' "$found" | wc -l | tr -d ' ')"
clean="$(printf '%s\n' "$found" | awk -F '\t' '$3 == ""' | wc -l | tr -d ' ')"
echo "$total models and clips, $clean with nothing to say; $(grep '^REAL seconds' "$out")"
if [ "${UPDATE:-}" = 1 ]; then
  { sed -n '/^#/p' "$expected" 2> /dev/null; printf '%s\n' "$found" | awk -F '\t' '$3 != ""'; } > "$expected.new"
  mv "$expected.new" "$expected"
  echo "updated the list"
  exit 0
fi
if diff <(sed '/^#/d' "$expected") <(printf '%s\n' "$found" | awk -F '\t' '$3 != ""'); then
  echo "as expected"
else
  echo "differs from $expected (< expected, > now)"
  exit 1
fi
