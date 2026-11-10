# narek-skills

[Claude Code](https://claude.com/claude-code) skills by domain: working standards for any project, game design, 3D modeling in Blender and Unity development. Each domain is a plugin of this marketplace, and each project turns on the domains and skills it needs.

## Domains

<!-- catalog:domains -->
| Domain | What it covers | Comes on with | Switch |
|---|---|---|---|
| [core](plugins/core/README.md) | Working standards for any project: musts with proofs and guides, receipts, verification against the project's own versions, fresh reviews and honest reports, the documentation layout, version notes, and the switches that choose a project's domains and skills. | game-design, modeling, unity-dev | `CORE_STANDARDS` |
| [game-design](plugins/game-design/README.md) | Game design for any engine: research, concepts with a hook, the game design document, core and meta loops, production order, game feel, calculated balance and pacing, and art direction with screenshot studies against references. | unity-dev | `GAME_DESIGN_STANDARDS` |
| [modeling](plugins/modeling/README.md) | 3D modeling in Blender for games and real-time apps: models, environments and modular kits, characters and animals with rigs, animation clips, automated mesh, character and motion checks, contact-sheet reviews, light baking and gated export. | unity-dev | `MODELING_STANDARDS` |
| [unity-dev](plugins/unity-dev/README.md) | Unity development: SOLID interface-based architecture and C# standards (VContainer, MessagePipe, UniTask) with automated audits, a tested code library, project setup, performance, UI, audio, VFX, NPC behavior, 3D models and animation in Unity, version notes and a toolchain check. | - | `UNITY_DEV_STANDARDS` |
<!-- /catalog -->

Each domain's README lists its skills. A domain brings the domains it builds on: installing unity-dev installs core, game-design and modeling, and turning it on in a project turns them on too, unless the project switches one off.

## How it works

Nothing loads unless you ask for it: Claude doesn't see the skills until you type a command, or until a project turns a domain on.

**Commands.** `/<domain>:standards` loads a domain's standards and guides, and the text after it is the task:

```text
/unity-dev:standards Create a new mobile puzzle game: <concept, mechanics, art style, models, screens...>
```

Every skill also has its own command, such as `/modeling:characters` or `/unity-dev:vfx`, to load that topic alone.

**Every session.** The first `/<domain>:standards` in a project turns that domain on there, and from then on its standards load at the start of every session, after `/clear`, after compaction and in subagents, so you don't type the command again and a long session doesn't lose them. The switches live under `env` in the project's `.claude/settings.json`:

| Switch | Turns on or off |
|---|---|
| `<DOMAIN>_STANDARDS`: `on` or `off` | a domain and all its skills, such as `UNITY_DEV_STANDARDS` |
| `<DOMAIN>_SKILL_<SKILL>`: `on` or `off` | one skill, whatever its domain says, such as `UNITY_DEV_SKILL_VFX` |

`/core:skills` shows what a project has on, turns domains and skills on or off, or looks at the project and turns on what it needs. Committed, the file sets them for the whole team; `.claude/settings.local.json` overrides them for one person.

**Two levels.** Each domain's standards have **musts**, the bar for the result, each with a proof that can fail and only you can change, and **guides**: methods known to work and failures seen, where Claude finds the solution for your project, tells you why, and records it in the project's `CLAUDE.md`. Checks write receipts in `docs/proofs/`; in a Unity project, a hook compares them with what changed when a turn ends.

**Verified, not trusted.** The guides and the code library can contain mistakes or fall behind new versions, and they say so. Claude checks every API, setting and library module it relies on against the official documentation or the source for your project's exact versions, and tells you when a guide turns out wrong. The guides' claims were checked against the official documentation and package sources (Unity 6.6, URP, VContainer 1.19, UniTask 2.5, MessagePipe 1.8, Addressables 4.1, Blender 5.2), and what can run was run.

## Install

```sh
claude plugin marketplace add anthropics/claude-plugins-official   # unity-dev needs its unity and csharp-lsp
claude plugin marketplace add NarekMynell/claude-skills
claude plugin install unity-dev@narek-skills     # or core, game-design, modeling
```

Or browse and install from `/plugin` inside Claude Code. Requires Claude Code (tested with 2.1.322). The hooks are bash scripts: on Windows they need Git Bash. Each domain's README lists what else it needs.

## Update

Third-party marketplaces don't auto-update by default. Turn it on once in `/plugin` → Marketplaces → narek-skills, or update by hand:

```sh
claude plugin marketplace update narek-skills
claude plugin update unity-dev@narek-skills
```

A project set up before the domains split (unity-dev 0.11 and earlier) keeps working: `UNITY_DEV_STANDARDS` brings the new domains with it. Run `/core:skills` there once to add their read rules, so their guides open without asking.

## Use in a team project

Commit a `.claude/settings.json` that lists the marketplaces, the plugins and the switches (`/core:skills` writes it, and `/unity-dev:new-project` for new Unity projects). Each teammate adds the marketplaces once, as in [Install](#install), and runs `claude plugin install <plugin>@narek-skills --scope project`; the standards then load in their sessions too.

## Contributing

Open Claude Code in this repository and ask it to add or change a skill or a domain. The architecture and the rules are in [CLAUDE.md](CLAUDE.md).
