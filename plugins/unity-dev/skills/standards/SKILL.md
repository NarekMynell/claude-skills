---
name: standards
description: Loads every unity-dev standard and guide - new projects, C# architecture and code rules, the tested code library, game design, UI, performance, audio, VFX, Blender 3D models, docs, the done checklist - and turns them on for every session in a Unity project. Add a task to start it right away; `off` and `on` switch every-session loading.
disable-model-invocation: true
argument-hint: "[task | on | off]"
allowed-tools:
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/skills/toolchain/scripts/check.sh *)
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# unity-dev standards

Follow the unity-dev standards strictly in all work for the rest of this session, and verify them as you use them. Decisions recorded in the project's `CLAUDE.md` and `.claude/rules/` take precedence over them. Where a standard turns out wrong, doesn't fit the project, or a different solution is clearly better, use the better one, tell the user why, and record it under **Decisions** in the project's `CLAUDE.md`.

## Verify before relying on them

These standards, the guides and the code library can contain mistakes, outdated facts, and advice that isn't the best practice for this project. They are strong defaults to check, not facts to trust. Checking is mandatory:

- **APIs, settings and versions.** Before using an API, attribute, setting, menu path, command or package id named in a guide, confirm it for the project's exact versions (`ProjectSettings/ProjectVersion.txt`, `Packages/packages-lock.json`): in the official documentation for that version, in the package source under `Library/PackageCache/`, or by compiling and running it. The guides and your training data both lag behind new releases.
- **What ran beats what is written.** A test, a build or the package source outranks the documentation, which outranks a guide or memory. Even Unity's documentation can describe behavior the installed version doesn't have: for 6000.6.2f1 it says a Mesh Collider mesh without Read/Write fails the build, and the build only warns. When sources disagree, rely on what ran, and report the disagreement.
- **Library code.** Review every file before it enters the project, as you would a colleague's pull request: lifetimes, cancellation, edge cases, allocations. It compiles there with no warnings, and its tests pass there.
- **Advice.** Before applying a rule, check that it fits the project. When the official documentation, a measurement or the project's needs contradict a guide, follow the evidence, and tell the user that the unity-dev guide needs the same fix.
- **Honest reports.** Say what you verified and how. Never present something as checked when it wasn't.

Links here are relative to `${CLAUDE_SKILL_DIR}`, and each guide links its own references relative to its folder. The plugin's root folder is two levels above this one.

## Start

Before the first task, read the [code standards](../code-standards/SKILL.md) and the [library catalog](../library/CATALOG.md).

## Guides

The guides are this plugin's other skills. They load only on the user's command, so the Skill tool refuses them: read their files with the Read tool instead. That is how these standards are meant to work.

Read every guide that matches the task before the work it covers, and read it again after the conversation is compacted. A large task, such as a whole game, touches several guides: plan with all of them, then read each again when its part of the work starts.

| Work | Guide |
|---|---|
| Creating a new Unity project | [new project](../new-project/SKILL.md). When the task goes on after the project exists, such as building the game, continue in the new project's folder in this session |
| Bringing an existing project under the standards | [adopt standards](../adopt-standards/SKILL.md) |
| Writing, refactoring or reviewing C# | [code standards](../code-standards/SKILL.md), its [resource lifetimes](../code-standards/references/resource-lifetimes.md) rules, and the references it links for the topic |
| Generic code, or a common system | [code library](../library/SKILL.md): check its [catalog](../library/CATALOG.md) before writing the code |
| A new feature area | [new domain](../new-domain/SKILL.md) |
| Screens, menus, HUDs, popups | [UI quality](../ui-quality/SKILL.md) |
| Frame rate, memory, load time, build size | [performance](../performance/SKILL.md) |
| Sounds and music | [audio design](../audio-design/SKILL.md) |
| Visual effects | [VFX](../vfx/SKILL.md) |
| Game concepts, mechanics, features | [game design](../game-design/SKILL.md) |
| 3D models, environments, characters | [game assets](../game-assets/SKILL.md), through the Blender MCP connector |
| README, CLAUDE.md, `docs/`, `.claude/rules/` | [project docs](../project-docs/SKILL.md) |
| Engine APIs that may have changed in recent Unity versions | the project's `docs/unity-version-notes.md`; to write or update it, [version notes](../version-notes/SKILL.md) |
| Unity CLI, Editor link, C# language server or Blender connector problems | [toolchain](../toolchain/SKILL.md) |

## Every task

- Drive the open Editor through the Unity CLI (`unity status`, `unity command`; syntax in the official `unity:unity-cli` skill) instead of hand-editing scene, prefab or asset files.
- Keep the docs current: a change that affects documented behavior updates the matching `docs/` file in the same change, and adding, renaming or removing a docs file updates the indexes in `README.md` and `CLAUDE.md`. New docs are concise, one topic per file, linked instead of duplicated.

## Before reporting a task as done

1. **Correct.** No errors or warnings from the C# language server or the Unity console. Checked in Play Mode where the change is visible.
2. **Best solution.** Nothing simpler or better; it scales with the expected growth without over-engineering.
3. **Architecture.** Right domain and assembly, dependency direction, DI instead of statics, interfaces where they belong.
4. **Performance.** No per-frame allocations or needless work; draw calls and memory within the project's budgets (`docs/performance-budgets.md`).
5. **Robust.** Every resource released by its owner on every path ([resource lifetimes](../code-standards/references/resource-lifetimes.md)): subscriptions, handles, tokens, buffers, created objects. Destroyed objects, cancellation and errors handled.
6. **Consistent.** Naming and structure rules followed; docs updated.
7. **Verified.** Every API, setting and library module the work relies on was checked for the project's versions, and the report says how.

If a check fails, fix it before moving on.

## When the user types the command

Arguments: `$ARGUMENTS`

Every-session loading is the `UNITY_DEV_STANDARDS` variable under `env` in the project's `.claude/settings.json`, which the team shares, or in `.claude/settings.local.json`, which is personal and wins over it. `on` loads these standards at the start of every session in the project, `off` doesn't. Check both files with the Read tool (a missing file sets nothing) and change them with Edit or Write, not through the shell; Claude Code asks the user to approve changes to them. Turning it on also needs this read rule, because outside the command nothing pre-approves reading the guides:

```json
{
  "env": { "UNITY_DEV_STANDARDS": "on" },
  "permissions": { "allow": ["Read(~/.claude/plugins/cache/*/unity-dev/**)"] }
}
```

1. **`on` or `off`.** If the arguments are exactly `on` or `off`, set the variable to that value in the file that sets it now, or in `.claude/settings.json` when neither does, and for `on` make sure the read rule is there. Confirm in one line and stop.
2. **Toolchain.** Run the toolchain check, exactly as written, with nothing added (it always exits 0): `bash ${CLAUDE_PLUGIN_ROOT}/skills/toolchain/scripts/check.sh "${CLAUDE_PROJECT_DIR}" "${CLAUDE_PLUGIN_DATA}"`. It prints nothing when the toolchain is fine. If it reports problems, list them for the user in a few lines with the command that fixes them, `/unity-dev:toolchain` (or `/unity-dev:version-notes` for the version notes), then go on.
3. **Every session.** Only in a Unity project, a folder with `ProjectSettings/ProjectVersion.txt`; a project created in this session gets the switch from the new-project template instead. If neither file sets the variable, merge the JSON above into `.claude/settings.json`, creating the file if needed. Tell the user in one line that the standards now load at the start of every session in this project, and that `/unity-dev:standards off` turns that off.
4. **Start**, as above.
5. **Task.** The arguments are the task: start it. Without arguments, tell the user in one line that the standards are loaded, and wait.
