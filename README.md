# narek-skills

[Claude Code](https://claude.com/claude-code) plugin `unity-dev` for professional Unity game development: architecture and C# standards, new-project setup, game design, UI, performance, audio and VFX quality bars, game-ready 3D models through Blender, project documentation, a tested code library and a toolchain check.

## How it works

You need one command. `/unity-dev:standards` gives Claude every guide in the plugin, and the text you type after it is the task:

```text
/unity-dev:standards Create a new mobile puzzle game: <concept, mechanics, art style, models, screens...>
```

Claude reads the guides the task needs, from the new-project setup to game design, code, UI and the Blender models, and decides what applies. It follows the standards strictly; where one doesn't fit your project and a different solution is clearly better, it uses that, tells you why and records it in the project's `CLAUDE.md`.

The guides and the code library can contain mistakes or fall behind new Unity and package versions, and they say so. Claude checks every API, setting and library module it relies on against the official documentation or the package source for your project's exact versions, reviews library code before copying it, and tells you when a guide turns out wrong.

Nothing loads unless you ask for it: Claude doesn't see the plugin's skills until you type a command, so they cost no context in other sessions.

| Command | Does |
|---|---|
| `/unity-dev:standards [task \| on \| off]` | Loads every standard and guide for the session, checks the toolchain, and turns the standards on for every session in a Unity project |

Every guide also has its own command, such as `/unity-dev:vfx`, `/unity-dev:new-project` or `/unity-dev:game-assets`, to load that topic alone. The plugins unity-dev depends on come from other publishers and keep their own behavior: the official Unity plugin's skills load automatically.

### Standards in every session

The first `/unity-dev:standards` in a project turns the standards on for that project. From then on they load at the start of every session there, and again after `/clear` and after the conversation is compacted, so you don't type the command again and a long session doesn't lose them. `/unity-dev:new-project` and `/unity-dev:adopt-standards` turn them on too. Other projects don't change.

The switch is `UNITY_DEV_STANDARDS` under `env` in the project's `.claude/settings.json`, next to a rule that lets those sessions read the plugin's guides without asking; Claude Code's trust dialog lists that rule the first time someone opens the folder. `/unity-dev:standards off` turns it off, and `/unity-dev:standards on` turns it back on. Committed, the file turns the standards on for the whole team; a teammate turns them off for themselves alone with `"UNITY_DEV_STANDARDS": "off"` under `env` in `.claude/settings.local.json`.

## Quality

- The unity-dev code library is covered by 172 automated tests: 143 Edit Mode and 29 Play Mode, 12 of which check what the guides claim about VContainer, MessagePipe, UniTask and Unity. They include allocation tests on hot paths and disposal tests on disposable types. The library compiles with no warnings on Unity 6000.6, and the Play Mode tests also pass in macOS and WebGL (IL2CPP) player builds. Run them with `dev/run-library-tests.sh`, `dev/run-library-tests.sh player` and `dev/run-library-tests.sh player WebGL`.
- Every C# example in the guides and module READMEs compiles against the real packages (`dev/library-tests/Assets/LibraryTests/SnippetCheck`).
- The guides' technical claims were checked against the official documentation and package sources for Unity 6.6, URP, VContainer 1.19, UniTask 2.5, MessagePipe 1.8, Addressables 4.1 and Blender 5.2, and the ones that can run were run: FBX exports from Blender into Unity, player builds, package behavior. Where a run contradicted the documentation, the guides follow the run. That lowers the risk of mistakes but doesn't remove it, which is why Claude verifies again in each project.
- The Blender scripts are tested headless against scenes with known results: `dev/run-blender-tests.sh`.
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
