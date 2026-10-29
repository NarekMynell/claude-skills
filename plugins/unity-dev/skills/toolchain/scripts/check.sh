#!/usr/bin/env bash
# unity-dev toolchain check, run by the standards and toolchain skills:
#   check.sh <project dir> <plugin data dir>
# Prints the problems it finds, and nothing when the toolchain is healthy or the folder isn't a Unity project.
# Network lookups are cached for a day in the data dir, next to the user's decisions.

project="${1:-${CLAUDE_PROJECT_DIR:-$PWD}}"
version_file="$project/ProjectSettings/ProjectVersion.txt"
[ -f "$version_file" ] || exit 0

cache_dir="${2:-${CLAUDE_PLUGIN_DATA:-${XDG_CACHE_HOME:-$HOME/.cache}/unity-dev}}"
mkdir -p "$cache_dir" 2>/dev/null || exit 0
decisions="$cache_dir/decisions"
problems=""

report() {
  problems="${problems}- $1
"
}

decided() {
  grep -qxF "$1" "$decisions" 2>/dev/null
}

is_fresh() {
  [ -s "$1" ] && [ -n "$(find "$1" -mmin -1440 2>/dev/null)" ]
}

refresh() {
  local file="$cache_dir/$1"
  shift
  is_fresh "$file" && return
  ("$@" > "$file.tmp" 2>/dev/null && mv "$file.tmp" "$file" || rm -f "$file.tmp") &
}

json_string() {
  sed -n "s/.*\"$1\": *\"\([^\"]*\)\".*/\1/p" "$cache_dir/$2" 2>/dev/null | head -n 1
}

is_version() {
  case "$1" in [0-9]*) return 0 ;; *) return 1 ;; esac
}

editor_version="$(sed -n 's/^m_EditorVersion: *//p' "$version_file" | tr -d '\r')"
manifest="$project/Packages/manifest.json"

unity_bin="$(command -v unity 2>/dev/null)"
if [ -z "$unity_bin" ] && [ -x "$HOME/.unity/bin/unity" ]; then
  unity_bin="$HOME/.unity/bin/unity"
fi

csharp_ls="$(command -v csharp-ls 2>/dev/null)"
if [ -z "$csharp_ls" ] && [ -x "$HOME/.dotnet/tools/csharp-ls" ]; then
  csharp_ls="$HOME/.dotnet/tools/csharp-ls"
fi

if [ -n "$unity_bin" ]; then
  refresh unity-cli-update.json "$unity_bin" self-update --check --format json
  refresh pipeline-versions.json "$unity_bin" pipeline list-versions --format json
fi
if [ -n "$csharp_ls" ] && command -v curl >/dev/null 2>&1; then
  refresh csharp-ls-versions.json curl -fsS --max-time 5 https://api.nuget.org/v3-flatcontainer/csharp-ls/index.json
fi
wait

if [ -z "$unity_bin" ]; then
  report "Unity CLI is not installed."
else
  cli_current="$("$unity_bin" --version 2>/dev/null | head -n 1 | tr -d '\r')"
  cli_latest="$(json_string latestVersion unity-cli-update.json)"
  if is_version "$cli_latest" && [ "$cli_current" != "$cli_latest" ]; then
    report "Unity CLI $cli_current: $cli_latest is available."
  fi
fi

pipeline_version="$(sed -n 's/.*"com\.unity\.pipeline": *"\([^"]*\)".*/\1/p' "$manifest" 2>/dev/null | head -n 1)"
if [ -z "$pipeline_version" ]; then
  if ! decided "pipeline-skip:$project"; then
    report "The Unity Pipeline package (com.unity.pipeline) is not installed, so the Unity CLI can't drive the Editor."
  fi
elif is_version "$pipeline_version"; then
  pipeline_latest="$(json_string latest pipeline-versions.json)"
  if is_version "$pipeline_latest" && [ "$pipeline_version" != "$pipeline_latest" ]; then
    report "Unity Pipeline package $pipeline_version: $pipeline_latest is available."
  fi
fi

if [ -z "$csharp_ls" ]; then
  report "The C# language server (csharp-ls) is not installed."
else
  ls_current="$("$csharp_ls" --version 2>/dev/null | sed -n 's/^csharp-ls, \([0-9][0-9.]*\).*/\1/p')"
  ls_latest="$(tr ',' '\n' < "$cache_dir/csharp-ls-versions.json" 2>/dev/null | tr -d '[]{}" \r\t' | sed -e '/-/d' -e '/^[0-9]/!d' | tail -n 1)"
  if is_version "$ls_current" && is_version "$ls_latest" && [ "$ls_current" != "$ls_latest" ]; then
    report "csharp-ls $ls_current: $ls_latest is available."
  fi
fi

if ! decided "relay-kept" && grep -qsE 'relay_(mac|win|linux)' "$HOME/.claude.json" "$project/.mcp.json"; then
  report "The deprecated Unity MCP relay server is configured. Unity recommends the Unity CLI instead."
fi

notes="$project/docs/unity-version-notes.md"
if [ ! -f "$notes" ]; then
  report "docs/unity-version-notes.md is missing (project uses Unity $editor_version)."
elif ! head -n 3 "$notes" | grep -qF "Covers Unity $editor_version."; then
  report "docs/unity-version-notes.md doesn't cover the project's Unity $editor_version."
fi

[ -z "$problems" ] && exit 0
printf 'unity-dev toolchain check, Unity %s project:\n%s' "$editor_version" "$problems"
