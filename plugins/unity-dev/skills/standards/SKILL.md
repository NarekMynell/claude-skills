---
name: standards
description: Loads all unity-dev standards for the rest of the session - C# architecture and code rules, the tested code library, the UI, performance, audio, VFX and game design quality bars, and the done checklist. Write a task after the command to start it right away.
disable-model-invocation: true
argument-hint: "[task]"
allowed-tools:
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/skills/toolchain/scripts/check.sh *)
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# unity-dev standards

The user loaded the unity-dev standards: follow them in all work for the rest of this session. Decisions recorded in the project's `CLAUDE.md` and `.claude/rules/` take precedence over them.

## Start

1. Run the toolchain check, exactly as written, with nothing added (it always exits 0): `bash ${CLAUDE_PLUGIN_ROOT}/skills/toolchain/scripts/check.sh "${CLAUDE_PROJECT_DIR}" "${CLAUDE_PLUGIN_DATA}"`. It prints nothing when the toolchain is fine. If it reports problems, list them for the user in a few lines with the command that fixes them, `/unity-dev:toolchain` (or `/unity-dev:version-notes` for the version notes), then go on.
2. Read the [code standards](../code-standards/SKILL.md) and the [library catalog](../library/CATALOG.md).

## Guides

The guides are this plugin's other skills. They load only on the user's command, so the Skill tool refuses them: read their files with the Read tool instead. That is how this skill is meant to work. Links are relative to this skill's folder, `${CLAUDE_SKILL_DIR}`, and each guide links its own references relative to its folder.

Read the matching guide before the work it covers, and read it again after the conversation is compacted.

| Work | Guide |
|---|---|
| Writing, refactoring or reviewing C# | [code standards](../code-standards/SKILL.md), and the references it links for the topic |
| Generic code, or a common system | [code library](../library/SKILL.md): check its [catalog](../library/CATALOG.md) before writing the code |
| A new feature area | [new domain](../new-domain/SKILL.md) |
| Screens, menus, HUDs, popups | [UI quality](../ui-quality/SKILL.md) |
| Frame rate, memory, load time, build size | [performance](../performance/SKILL.md) |
| Sounds and music | [audio design](../audio-design/SKILL.md) |
| Visual effects | [VFX](../vfx/SKILL.md) |
| Game concepts, mechanics, features | [game design](../game-design/SKILL.md) |
| Engine APIs that may have changed in recent Unity versions | the project's `docs/unity-version-notes.md` |
| 3D models | the blender plugin: suggest `/blender:game-assets` to the user |

## Every task

- Drive the open Editor through the Unity CLI (`unity status`, `unity command`; syntax in the official `unity:unity-cli` skill) instead of hand-editing scene, prefab or asset files.
- Keep the docs current: a change that affects documented behavior updates the matching `docs/` file in the same change, and adding, renaming or removing a docs file updates the indexes in `README.md` and `CLAUDE.md`. New docs are concise, one topic per file, linked instead of duplicated.

## Before reporting a task as done

1. **Correct.** No errors or warnings from the C# language server or the Unity console. Checked in Play Mode where the change is visible.
2. **Best solution.** Nothing simpler or better; it scales with the expected growth without over-engineering.
3. **Architecture.** Right domain and assembly, dependency direction, DI instead of statics, interfaces where they belong.
4. **Performance.** No per-frame allocations or needless work; draw calls and memory within the project's budgets (`docs/performance-budgets.md`).
5. **Robust.** Destroyed objects, cancellation, disposed subscriptions, errors.
6. **Consistent.** Naming and structure rules followed; docs updated.

If a check fails, fix it before moving on.

## Task

$ARGUMENTS

If no task follows the heading above, tell the user in one line that the standards are loaded, and wait.
