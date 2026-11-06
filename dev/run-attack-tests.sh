#!/usr/bin/env bash
# Runs the scenes an adversarial review built to fool inspect_character.py, from both sides: real defects that must fail, and
# good characters that must pass. Each verdict must match, or be listed in dev/blender/attacks/accepted.txt with its reason.
# An accepted case that now matches is reported too, so the list stays true.
# Usage: dev/run-attack-tests.sh [path-to-blender]
set -uo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
blender="${1:-blender}"
out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT
export ATTACK_OUT="$out/renders"
status=0
for name in defects_1 defects_2 defects_3 clean_1 clean_2 clean_3 cuts_1 cuts_2 sweeps mixed_4 mixed_5 mixed_6 mixed_7 mixed_8 mixed_9; do
  "$blender" -b --factory-startup --python-exit-code 1 --python "$root/dev/blender/attacks/$name.py" -- > "$out/$name.log" 2>&1
done
cat "$out"/*.log | grep -E '^\[(ok  |WRONG|CRASH)\]' > "$out/all.txt"
accepted="$root/dev/blender/attacks/accepted.txt"
while IFS= read -r line; do
  name="$(printf '%s' "$line" | sed -E 's/^\[[A-Z a-z]+\] ([^:]+):.*/\1/')"
  if grep -q "^$name:" "$accepted"; then continue; fi
  echo "$line" | cut -c1-200
  status=1
done < <(grep -E '^\[(WRONG|CRASH)\]' "$out/all.txt")
while IFS= read -r line; do
  name="${line%%:*}"
  [ -n "$name" ] || continue
  case "$name" in \#*) continue ;; esac
  if grep -q -E "^\[ok  \] $name:" "$out/all.txt"; then
    echo "accepted, and now right: $name"
    status=1
  fi
done < "$accepted"
echo "$(wc -l < "$out/all.txt" | tr -d ' ') cases, $(grep -c -E '^\[ok  \]' "$out/all.txt") right, $(grep -c -E '^\[(WRONG|CRASH)\]' "$out/all.txt") accepted or wrong"
exit $status
