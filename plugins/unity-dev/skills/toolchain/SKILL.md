---
name: toolchain
description: Checks, repairs and updates the Unity toolchain for Claude Code - Unity CLI, the Unity Pipeline package for live Editor control, the official Unity plugin, the C# language server, and the Blender connector.
disable-model-invocation: true
allowed-tools:
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/skills/toolchain/scripts/check.sh *)
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# Unity toolchain

Every tool must be **installed**, **reachable** and **up to date**. When an update is available, apply it without asking, unless the user has said otherwise. If a fix fails, stop and report the problem with the command and its output.

## Check

Run this command exactly as written, with nothing added (it always exits 0): `bash ${CLAUDE_PLUGIN_ROOT}/skills/toolchain/scripts/check.sh "${CLAUDE_PROJECT_DIR}" "${CLAUDE_PLUGIN_DATA}"`. In a Unity project it checks the tools below and prints only the problems; `/unity-dev:standards` runs the same check. Fix what it reports, plus any problem the user describes that it doesn't cover, such as the live Editor connection or the Blender connector.

## Tools

| Tool | Check | Fix or update |
|---|---|---|
| Unity CLI | `unity --version`; `unity self-update --check --format json` | Missing: install it as described in the `unity:unity-cli` skill. Update: `unity self-update --yes`, then `unity skill refresh --yes` (refreshes skills the CLI installed, if any). |
| Unity Pipeline package (`com.unity.pipeline`, Editor side of the CLI connection) | `unity pipeline list --format json` (needs a running Editor) | Missing: `unity pipeline install --project-path <project>`. Update: `unity pipeline upgrade --project-path <project>`. |
| Live Editor connection | `unity status --format json` shows the project with state `ready` | Ask the user to open the project in the Editor. If it doesn't connect, check for Safe Mode (compile errors) with `unity pipeline list` and fix the errors first. |
| Unity plugin for Claude Code (`unity@claude-plugins-official`) | `claude plugin list --json` | Installed automatically as a unity-dev dependency. Update: `claude plugin update unity@claude-plugins-official`. |
| C# language server | `csharp-ls --version` (also try `~/.dotnet/tools/csharp-ls`); plugin `csharp-lsp@claude-plugins-official` in `claude plugin list --json` | Server: `dotnet tool install --global csharp-ls`, update with `dotnet tool update --global csharp-ls`. The plugin is installed automatically as a unity-dev dependency. If the server is installed but not found, `~/.dotnet/tools` is missing from the PATH that Claude Code sees. |
| Blender connector | Only before 3D work: the Blender MCP `get_objects_summary` tool responds | Ask the user to start Blender with the connector enabled. |

Plugin updates and installs apply after Claude Code restarts: tell the user. Third-party marketplaces don't auto-update by default; the user enables it once in `/plugin` → Marketplaces.

## Editor control: Unity CLI, not the relay MCP server

- Drive the open Editor with `unity command ... --caller plugin --skill <skill>` and the other connected-Editor commands documented in the `unity:unity-cli` skill. Each call takes 200–600 ms with no recompile.
- `unity mcp` exposes the same Editor commands as MCP tools. Register it with `unity mcp configure claude-code` only if the user wants tool-style access.
- The older relay server from the AI Assistant package (`~/.unity/relay/...`, often registered as `unity-mcp`) is **deprecated**: its own documentation says to use the Unity CLI instead. When it is configured, tell the user and offer to switch. If they decline, add the line `relay-kept` to `${CLAUDE_PLUGIN_DATA}/decisions` so the check stops reporting it. If the user doesn't want the Pipeline package in a project, add `pipeline-skip:<absolute project path>` to the same file.

## Unity version notes

When the check reports that `docs/unity-version-notes.md` is missing or covers a different Unity version than `ProjectSettings/ProjectVersion.txt`, write the notes as the [version notes guide](../version-notes/SKILL.md) describes.

## After fixing

Run the check again and confirm it prints nothing. Report what was installed or updated, from which version to which.
