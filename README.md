# narek-skills

[Claude Code](https://claude.com/claude-code) plugins for professional Unity game development, Blender asset creation and project documentation. Install only the plugins you need.

| Plugin | Adds |
|---|---|
| `core` | `project-docs`: one documentation layout for people and Claude (README, CLAUDE.md, `docs/`, `.claude/rules/`) |
| `unity-dev` | C# architecture and code standards, new-project setup, adopting the standards in an existing project, new domains, performance, UI, audio, VFX and game design quality bars, Unity version notes, a reusable code library, and a session-start toolchain check |
| `blender` | `game-assets`: game-ready models through the Blender MCP connector, with automated mesh validation, multi-angle renders and export to Unity |

## Quality

- The unity-dev code library is covered by 103 automated tests (93 Edit Mode, 10 Play Mode), with allocation tests on its hot paths, and compiles with no warnings on Unity 6000.6. Run them with `dev/run-library-tests.sh`.
- The Blender scripts are tested headless against meshes with known defects.
- `claude plugin validate` passes for the marketplace and every plugin.

## Requirements

- Claude Code; tested with 2.1.312.
- **unity-dev:** the [Unity CLI](https://docs.unity.com/en-us/unity-cli) and the C# language server `csharp-ls` (`dotnet tool install --global csharp-ls`). Installing unity-dev also installs its dependencies: `core`, the official Unity plugin and `csharp-lsp`. In every Unity project, the session-start check reports what is missing or outdated. The check is a bash script; on Windows it needs Git Bash.
- **blender:** Blender with the Blender MCP connector.

## Install

```sh
claude plugin marketplace add NarekMynell/claude-skills
claude plugin install unity-dev@narek-skills
```

Or browse and install from `/plugin` inside Claude Code.

## Update

Third-party marketplaces don't auto-update by default. Turn it on once in `/plugin` → Marketplaces → narek-skills, or update by hand:

```sh
claude plugin marketplace update narek-skills
claude plugin update unity-dev@narek-skills
```

## Use in a team project

Commit a `.claude/settings.json` that lists the marketplace and the plugins (`unity-dev:new-project` writes it for new projects). Each teammate then runs `claude plugin install unity-dev@narek-skills --scope project` once.

## Contributing

Open Claude Code in this repo and ask it to add or change a skill. The conventions are in [CLAUDE.md](CLAUDE.md).
