---
name: standards
description: Loads the unity-dev standards and guides - new projects, C# architecture and code rules, the tested code library, UI, performance, audio, VFX, NPC behavior, 3D models and animation in Unity, the done checklist - with core, game-design and modeling, and turns them on for every session in a Unity project. Add a task to start it right away; `off` and `on` switch every-session loading.
disable-model-invocation: true
argument-hint: "[task | on | off]"
allowed-tools:
  - Bash(bash ${CLAUDE_PLUGIN_ROOT}/skills/toolchain/scripts/check.sh *)
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
  - Read(~/.claude/plugins/cache/*/core/**)
  - Read(~/.claude/plugins/cache/*/game-design/**)
  - Read(~/.claude/plugins/cache/*/modeling/**)
---

# unity-dev standards

Unity development, under the core standards. The game's design comes from `game-design`, its models, characters and clips from `modeling`; these guides build the game and prove it in Unity.

## Musts

| Area | The bar | Proof, before the work counts as done | Guide |
|---|---|---|---|
| Architecture | Modular, SOLID, interface-based, DI through VContainer. Each capability is an interface (such as `IMovable`, `IShooter`); an object with several implements them all; whoever uses an object sees only the capability it needs. Inheritance only for a true is-a; no singletons or mutable statics | `ProjectArchitectureTests` green, the capability map in `docs/architecture.md` included: that is the floor. A [fresh review](references/reviews.md#architecture) judges the design | [code standards](../code-standards/SKILL.md) |
| JSON | Through Newtonsoft (`com.unity.nuget.newtonsoft-json`), never `JsonUtility` | Code review | [code standards](../code-standards/SKILL.md) |
| Optimization | Equal to beauty: as beautiful and as cheap as possible. Nothing is paid for that the player can't see: what stands still is static, light that doesn't change is baked, work off screen stops | `BudgetTests`, `OffScreenTests` green; `SceneCostAudit` clean | [performance](../performance/SKILL.md) |
| Models in Unity | Imported as built: root at rotation 0 and scale 1, facing +Z, real size. Each unique model one prefab, placed many times | Captures next to a 1 m cube and from the game's camera, reviewed | [models](../models/SKILL.md) |
| Colliders | What looks solid stops the player, nothing else does, and characters stand on the ground | `ColliderAudit` clean | [models](../models/SKILL.md) |
| Motion in the game | Natural in the running game: planted feet never slide, at every speed; speed fits the body; weight and overlap survive blending, IK and steering, nothing robotic | `LocomotionTests` in Play Mode; frames of the running game reviewed | [animation](../animation/SKILL.md) |
| Behavior | Actors rest, have reasons, react, and don't walk through each other | `CrowdOverlapMeter` and `ActivityShares` in Play Mode at peak density; frames of the running game reviewed | [NPC behavior](../npc-behavior/SKILL.md) |
| UI | Designed for this game: no template or AI look, no capsule containers by default, one radius scale, nothing stretched, a small HUD | `UiAudit` clean against the project's tokens at each aspect ratio; device-size critique against references | [UI quality](../ui-quality/SKILL.md) |

## Verify before relying on them

The core rule holds, with Unity's sources: the project's versions in `ProjectSettings/ProjectVersion.txt` and `Packages/packages-lock.json`; Unity's documentation for that version, the package source under `Library/PackageCache/`, or a run. **Library code:** review every file before it enters the project. It compiles there with no warnings, and its tests pass there.

Links here are relative to `${CLAUDE_SKILL_DIR}`.

## Start

Before the first C#, read the [code standards](../code-standards/SKILL.md) and the [library catalog](../library/CATALOG.md). A whole game follows the production order of `game-design:game-design`.

## Guides

| Work | Guide |
|---|---|
| Creating a new Unity project | [new project](../new-project/SKILL.md), then continue in its folder |
| Bringing in an existing project | [adopt standards](../adopt-standards/SKILL.md) |
| Writing, refactoring or reviewing C# | [code standards](../code-standards/SKILL.md), with the references it links |
| Generic code, a common system | [code library](../library/SKILL.md): its [catalog](../library/CATALOG.md) first |
| A new feature area of the code, a code domain | [new domain](../new-domain/SKILL.md) |
| Screens, menus, HUDs | [UI quality](../ui-quality/SKILL.md) |
| Performance, lighting | [performance](../performance/SKILL.md) |
| Sounds and music | [audio design](../audio-design/SKILL.md) |
| Visual effects | [VFX](../vfx/SKILL.md) |
| Models and characters in Unity: export settings, import, Humanoid avatars, materials, LODs, colliders, prefabs | [models](../models/SKILL.md) |
| Animation in Unity: import, root motion, feet on the ground, held props | [animation](../animation/SKILL.md), after [models](../models/SKILL.md) |
| How actors move and behave | [NPC behavior](../npc-behavior/SKILL.md) |
| Unity APIs that may have changed recently, Unity's version notes | the project's `docs/unity-version-notes.md`; to write or update it, [version notes](../version-notes/SKILL.md) |
| Unity CLI or language server problems | [toolchain](../toolchain/SKILL.md) |
| A fresh review of the architecture, optimization, UI or motion | [reviews](references/reviews.md) |

## Every task

Drive the open Editor through the Unity CLI (`unity status`, `unity command`; syntax in the official `unity:unity-cli` skill) instead of hand-editing scene, prefab or asset files.

## Before reporting a task as done

The core checklist, with Unity's checks: no errors or warnings from the C# language server or the Unity console, checked in Play Mode where the change is visible; every resource released by its owner on every path ([resource lifetimes](../code-standards/references/resource-lifetimes.md)), destroyed objects handled.

## When the user types the command

Arguments: `$ARGUMENTS`

Every-session loading is `UNITY_DEV_STANDARDS` under `env` in the project's `.claude/settings.json`, which the team shares, or `.claude/settings.local.json`, which is personal and wins. It brings core, game-design and modeling, whose standards load with this command too, unless the project switches one off; their `core:skills` guide describes every switch. Check both files with the Read tool (a missing file sets nothing), and change them with Edit or Write, not through the shell; Claude Code asks the user to approve changes to them. Turning it on also needs the read rules, because outside a command nothing pre-approves reading the guides:

```json
{
  "env": { "UNITY_DEV_STANDARDS": "on" },
  "permissions": { "allow": [
    "Read(~/.claude/plugins/cache/*/unity-dev/**)",
    "Read(~/.claude/plugins/cache/*/core/**)",
    "Read(~/.claude/plugins/cache/*/game-design/**)",
    "Read(~/.claude/plugins/cache/*/modeling/**)"
  ] }
}
```

1. **`on` or `off`.** If the arguments are exactly `on` or `off`, set the variable to that value in the file that sets it now, or in `.claude/settings.json` when neither does, and for `on` make sure the read rules are there. Confirm in one line and stop.
2. **Toolchain.** Run the toolchain check, exactly as written, with nothing added (it always exits 0): `bash ${CLAUDE_PLUGIN_ROOT}/skills/toolchain/scripts/check.sh "${CLAUDE_PROJECT_DIR}" "${CLAUDE_PLUGIN_DATA}"`. It prints nothing when the toolchain is fine. If it reports problems, list them for the user in a few lines with the command that fixes them, `/unity-dev:toolchain` (or `/unity-dev:version-notes` for the version notes), then go on.
3. **Every session.** Only in a Unity project, a folder with `ProjectSettings/ProjectVersion.txt`; a project created in this session gets the switch from the new-project template instead. If neither file sets the variable, merge the JSON above into `.claude/settings.json`, creating the file if needed. A project set up before the domains split has the variable with only unity-dev's read rule: add the others. Tell the user in one line that unity-dev, with core, game-design and modeling, now loads at the start of every session in this project, that `/unity-dev:standards off` turns that off, and that `/core:skills` switches a part off, such as modeling in a 2D game.
4. **Start**, as above.
5. **Task.** The arguments are the task: start it. Without arguments, tell the user in one line that the standards are loaded, and wait.
