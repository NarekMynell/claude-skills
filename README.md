# narek-skills

[Claude Code](https://claude.com/claude-code) plugin `unity-dev` for professional Unity game development: architecture and C# standards, new-project setup, game design, UI, performance, audio and VFX quality bars, game-ready 3D models through Blender, project documentation, a tested code library and a toolchain check.

## How it works

You need one command. `/unity-dev:standards` gives Claude every guide in the plugin, and the text you type after it is the task:

```text
/unity-dev:standards Create a new mobile puzzle game: <concept, mechanics, art style, models, screens...>
```

Claude reads the guides the task needs, from the new-project setup to game design, code, UI and the Blender models, and decides what applies. It follows the standards strictly; where one doesn't fit your project and a different solution is clearly better, it uses that, tells you why and records it in the project's `CLAUDE.md`.

Nothing loads unless you ask for it: Claude doesn't see the plugin's skills until you type a command, so they cost no context in other sessions.

| Command | Does |
|---|---|
| `/unity-dev:standards [task \| on \| off]` | Loads every standard and guide for the session, checks the toolchain, and turns the standards on for every session in a Unity project |

Every guide also has its own command, such as `/unity-dev:vfx`, `/unity-dev:new-project` or `/unity-dev:game-assets`, to load that topic alone. The plugins unity-dev depends on come from other publishers and keep their own behavior: the official Unity plugin's skills load automatically.

### Standards in every session

The first `/unity-dev:standards` in a project turns the standards on for that project. From then on they load at the start of every session there, and again after `/clear` and after the conversation is compacted, so you don't type the command again and a long session doesn't lose them. `/unity-dev:new-project` and `/unity-dev:adopt-standards` turn them on too. Other projects don't change.

The switch is `UNITY_DEV_STANDARDS` under `env` in the project's `.claude/settings.json`, next to a rule that lets those sessions read the plugin's guides without asking; Claude Code's trust dialog lists that rule the first time someone opens the folder. `/unity-dev:standards off` turns it off, and `/unity-dev:standards on` turns it back on. Committed, the file turns the standards on for the whole team; a teammate turns them off for themselves alone with `"UNITY_DEV_STANDARDS": "off"` under `env` in `.claude/settings.local.json`.

## Quality

- The unity-dev code library is covered by 103 automated tests (93 Edit Mode, 10 Play Mode), with allocation tests on its hot paths, and compiles with no warnings on Unity 6000.6. Run them with `dev/run-library-tests.sh`.
- The Blender scripts are tested headless against meshes with known defects.
- `claude plugin validate` passes for the marketplace and the plugin.

## Requirements

- Claude Code; tested with 2.1.312.
- **unity-dev:** the [Unity CLI](https://docs.unity.com/en-us/unity-cli) and the C# language server `csharp-ls` (`dotnet tool install --global csharp-ls`). Installing unity-dev also installs its dependencies, the official Unity plugin and `csharp-lsp`. The toolchain check and the every-session loading are bash scripts; on Windows they need Git Bash.
- For 3D models: Blender with the Blender MCP connector.

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

Commit a `.claude/settings.json` that lists the marketplace and the plugin and turns the standards on (`/unity-dev:new-project` writes it for new projects). Each teammate then runs `claude plugin install unity-dev@narek-skills --scope project` once, and the standards load in their sessions too.

## Contributing

Open Claude Code in this repo and ask it to add or change a skill. The conventions are in [CLAUDE.md](CLAUDE.md).
