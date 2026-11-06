---
name: standards
description: Loads every unity-dev standard and guide - new projects, C# architecture and code rules, the tested code library, game design, UI, performance, audio, VFX, Blender 3D models, characters and animation, docs, the done checklist - and turns them on for every session in a Unity project. Add a task to start it right away; `off` and `on` switch every-session loading.
disable-model-invocation: true
argument-hint: "[task | on | off]"
allowed-tools:
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/skills/toolchain/scripts/check.sh *)
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# unity-dev standards

Two levels apply to all work for the rest of this session.

**Musts** are the bar for the result. A must holds whatever the task's wording, the schedule, a usage limit or Claude's own notes say. Only the user changes one, in their own words, naming it; a decision Claude records doesn't. A brief that asks for something else changes the means, not the bar: "no third-party assets" removes a source, and motion must still look natural. When a must can't be met, say so, with the numbers.

**Guides** are everything else: methods known to work, failures seen, strong defaults. The solution is Claude's to find by thinking it through for this project, inside the guides or outside them. Take what is clearly best, tell the user why, and record it under **Decisions** in the project's `CLAUDE.md`. Decisions there and in `.claude/rules/` beat guides, never musts.

## Musts

| Area | The bar | Proof, before the work counts as done |
|---|---|---|
| Architecture | Modular, SOLID, interface-based, DI through VContainer. Each capability is an interface (such as `IMovable`, `IShooter`); an object with several implements them all; whoever uses an object sees only the capability it needs. Inheritance only for a true is-a; no singletons or mutable statics | `ProjectArchitectureTests` green, the capability map in `docs/architecture.md` included |
| JSON | Through Newtonsoft (`com.unity.nuget.newtonsoft-json`), never `JsonUtility` | `ProjectArchitectureTests` green |
| Optimization | Equal to beauty: as beautiful and as cheap as possible. Nothing is paid for that the player can't see: what stands still is static, light that doesn't change is baked, work off screen stops | `BudgetTests`, `OffScreenTests` green; `SceneCostAudit` clean |
| Art | A current, beautiful look from references, one style throughout. One screen at final quality before mass production | `study_screenshot.py` on real game screenshots: no gaps against references; a written critique |
| Models | No stacked or hidden faces, no artifacts, no visible facets on curves | `validate_mesh.py` passes; contact-sheet critique finds nothing |
| Characters, animals | Nothing visibly pokes through anything: in any variant, in any pose, from the game's camera. However built | `inspect_character.py` over all variants; sheet with `GAME_VIEW` |
| Motion, behavior | Natural. Planted feet never slide, in the running game, at every speed; speed fits the body; weight and overlap, nothing robotic. Actors rest, have reasons, react, and don't walk through each other | `inspect_animation.py` per clip; `LocomotionTests` in Play Mode; frames of the running game reviewed |
| UI | Designed for this game: no template or AI look, no capsule containers by default, one radius scale, nothing stretched, a small HUD | `UiAudit` clean against the project's tokens at each aspect ratio; device-size critique against references |
| Balance | Calculated, every number justified; never boring, never a wall | A simulation of the real game logic per player type, from the first playable; `PacingAnalyzer` clean against targets stated first |

How the work runs:

- **The proof stands whatever the pipeline.** A custom format, shader skinning or UI built from code doesn't replace a check: bring the result to where the check can see it, or write an equal check and prove it catches the same defect.
- **Receipts.** Checks write their results to `docs/proofs/` themselves, and a hook compares them with what changed. A must without a passing, current receipt is unproven: say so. What a project truly has no use for goes in `docs/proofs/not-applicable.txt`, as `family: reason`; a failure the user accepted, as `receipt: their words`.
- **Subagents know only their brief.** Each brief names the guide files, by full path, the checks and the bar.
- **Fresh eyes.** At every milestone a new agent reviews the work against the guides: [how](references/fresh-review.md).
- **Ask early.** What only the user can give (downloads, accounts, clips, fonts, references) is asked for at the start of a long task, all at once. Without it, go on with the best substitute, and report what stays unproven.
- **Limits end work, not the bar.** Near a usage or time limit, stop and report what isn't proven. Never skip a check or a review round to finish.
- **Honest reports.** Say what ran, with its numbers, and what didn't. In plain words: what the player would see, not a check's name.

## Verify before relying on them

These standards, the guides and the code library can contain mistakes and outdated facts. Checking is mandatory:

- **APIs, settings and versions.** Before using anything a guide names, confirm it for the project's exact versions (`ProjectSettings/ProjectVersion.txt`, `Packages/packages-lock.json`): in the official documentation, in the package source under `Library/PackageCache/`, or by running it.
- **What ran beats what is written.** A test, a build or the package source outranks the documentation, which outranks a guide or memory. Report disagreements.
- **Library code.** Review every file before it enters the project. It compiles there with no warnings, and its tests pass there.
- **Advice.** When the documentation, a measurement or the project's needs contradict a guide, follow the evidence, and tell the user the guide needs the same fix. A wrong must or check is reported to the user, not dropped.

Links here are relative to `${CLAUDE_SKILL_DIR}`.

## Start

Before the first task, read the [code standards](../code-standards/SKILL.md) and the [library catalog](../library/CATALOG.md).

## Guides

The guides are this plugin's other skills. The Skill tool refuses them: read their files with the Read tool, as these standards intend.

Read every guide that matches the task before the work it covers, with the references it links for that work, and read them again after the conversation is compacted. A whole game touches nearly all of them: follow its [production order](../game-design/SKILL.md#production-order).

| Work | Guide |
|---|---|
| Creating a new Unity project | [new project](../new-project/SKILL.md), then continue in its folder |
| Bringing an existing project under the standards | [adopt standards](../adopt-standards/SKILL.md) |
| Writing, refactoring or reviewing C# | [code standards](../code-standards/SKILL.md), with its [capabilities](../code-standards/references/capabilities.md), [organization](../code-standards/references/code-organization.md), [DI](../code-standards/references/dependency-injection.md), [messaging](../code-standards/references/messaging-and-state.md) and [resource lifetimes](../code-standards/references/resource-lifetimes.md) references |
| Generic code, or a common system | [code library](../library/SKILL.md): check its [catalog](../library/CATALOG.md) before writing the code |
| A new feature area | [new domain](../new-domain/SKILL.md) |
| Game concepts, mechanics, features | [game design](../game-design/SKILL.md) |
| Economy, progression, pacing, rewards | [balance](../game-design/references/balance.md) |
| Colors, style, environments, the game's look | [art direction](../art-direction/SKILL.md) |
| Screens, menus, HUDs, popups, world markers | [UI quality](../ui-quality/SKILL.md) |
| Frame rate, memory, load time, build size, lighting setup | [performance](../performance/SKILL.md) |
| Sounds and music | [audio design](../audio-design/SKILL.md) |
| Visual effects | [VFX](../vfx/SKILL.md) |
| 3D models and environments | [game assets](../game-assets/SKILL.md), through the Blender MCP connector |
| Characters and animals: bases, variants, rigging, skinning | [characters](../characters/SKILL.md), after [game assets](../game-assets/SKILL.md) |
| Animation: clips, locomotion, IK, held props, keying motion | [animation](../animation/SKILL.md) |
| How people and animals move through the world and behave | [NPC behavior](../npc-behavior/SKILL.md) |
| README, CLAUDE.md, `docs/`, `.claude/rules/` | [project docs](../project-docs/SKILL.md) |
| Engine APIs that may have changed recently | the project's `docs/unity-version-notes.md`; to update it, [version notes](../version-notes/SKILL.md) |
| Unity CLI, Editor link, language server or Blender connector problems | [toolchain](../toolchain/SKILL.md) |

## Every task

- Drive the open Editor through the Unity CLI (`unity status`, `unity command`; syntax in the official `unity:unity-cli` skill) instead of hand-editing scene, prefab or asset files.
- Keep the docs current, in the same change, and the indexes in `README.md` and `CLAUDE.md` with them.

## Before reporting a task as done

1. **Proof.** The musts the work touches have their proof, on the latest state, and the report gives the numbers.
2. **Correct.** No errors or warnings from the C# language server or the Unity console. Checked in Play Mode where the change is visible.
3. **Best solution.** Name the alternatives you weighed, and why this one wins.
4. **Robust.** Every resource released by its owner on every path ([resource lifetimes](../code-standards/references/resource-lifetimes.md)). Destroyed objects, cancellation and errors handled.
5. **Consistent.** Naming and structure rules followed; docs updated.
6. **Verified.** APIs, settings and library modules checked for the project's versions; the report says how.

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
