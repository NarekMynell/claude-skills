# narek-skills

[Claude Code](https://claude.com/claude-code) plugins for professional Unity game development, Blender asset creation and project documentation. Install only the plugins you need.

| Plugin | Adds |
|---|---|
| `core` | `project-docs`: one documentation layout for people and Claude (README, CLAUDE.md, `docs/`, `.claude/rules/`) |
| `unity-dev` | C# architecture and code standards, new-project setup, adopting the standards in an existing project, new domains, performance, UI, audio, VFX and game design quality bars, Unity version notes, a tested code library and a toolchain check |
| `blender` | `game-assets`: game-ready models through the Blender MCP connector, with automated mesh validation, multi-angle renders and export to Unity |

## How it works

Nothing in these plugins loads unless you ask for it. Claude doesn't see their skills until you type a command, so they cost no context in other sessions. A command loads its instructions for the rest of the session, and text typed after it is the task.

| Command | Does |
|---|---|
| `/unity-dev:standards [task \| on \| off]` | Loads every unity-dev standard: code rules, the code library, the UI, performance, audio, VFX and game design guides, and the done checklist. Checks the toolchain first. The first run in a project turns them on for every session there |
| `/unity-dev:new-project [game idea]` | Creates a new Unity project with the standards |
| `/unity-dev:adopt-standards` | Brings an existing Unity project under the standards |
| `/unity-dev:toolchain` | Checks and updates the Unity CLI, the Editor link and the C# language server |
| `/blender:game-assets [model]` | Builds a game-ready 3D model in Blender |
| `/core:project-docs` | Sets up or tidies a project's documentation |

Each unity-dev guide also has its own command, such as `/unity-dev:vfx` or `/unity-dev:code-standards`, to load that topic alone. The plugins unity-dev depends on come from other publishers and keep their own behavior: the official Unity plugin's skills load automatically.

### Standards in every session

The first `/unity-dev:standards` in a project turns the standards on for that project. From then on they load at the start of every session there, and again after `/clear` and after the conversation is compacted, so you don't type the command again and a long session doesn't lose them. `/unity-dev:new-project` and `/unity-dev:adopt-standards` turn them on too. Other projects don't change.

The switch is `UNITY_DEV_STANDARDS` under `env` in the project's `.claude/settings.json`, next to a rule that lets those sessions read the plugin's guides without asking; Claude Code's trust dialog lists that rule the first time someone opens the folder. `/unity-dev:standards off` turns it off, and `/unity-dev:standards on` turns it back on. Committed, the file turns the standards on for the whole team; a teammate turns them off for themselves alone with `"UNITY_DEV_STANDARDS": "off"` under `env` in `.claude/settings.local.json`.

## Quality

- The unity-dev code library is covered by 103 automated tests (93 Edit Mode, 10 Play Mode), with allocation tests on its hot paths, and compiles with no warnings on Unity 6000.6. Run them with `dev/run-library-tests.sh`.
- The Blender scripts are tested headless against meshes with known defects.
- `claude plugin validate` passes for the marketplace and every plugin.

## Requirements

- Claude Code; tested with 2.1.312.
- **unity-dev:** the [Unity CLI](https://docs.unity.com/en-us/unity-cli) and the C# language server `csharp-ls` (`dotnet tool install --global csharp-ls`). Installing unity-dev also installs its dependencies, the official Unity plugin and `csharp-lsp`. The toolchain check and the every-session loading are bash scripts; on Windows they need Git Bash.
- **blender:** Blender with the Blender MCP connector.

## Install

```sh
claude plugin marketplace add NarekMynell/claude-skills
claude plugin install unity-dev@narek-skills
claude plugin install blender@narek-skills
claude plugin install core@narek-skills
```

Or browse and install from `/plugin` inside Claude Code.

## Update

Third-party marketplaces don't auto-update by default. Turn it on once in `/plugin` → Marketplaces → narek-skills, or update by hand:

```sh
claude plugin marketplace update narek-skills
claude plugin update unity-dev@narek-skills
```

## Use in a team project

Commit a `.claude/settings.json` that lists the marketplace and the plugins and turns the standards on (`/unity-dev:new-project` writes it for new projects). Each teammate then runs `claude plugin install unity-dev@narek-skills --scope project` once, and the standards load in their sessions too.

## Contributing

Open Claude Code in this repo and ask it to add or change a skill. The conventions are in [CLAUDE.md](CLAUDE.md).
