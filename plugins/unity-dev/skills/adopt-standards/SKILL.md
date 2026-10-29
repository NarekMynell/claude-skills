---
name: adopt-standards
description: Brings an existing Unity project under the unity-dev standards without breaking it - CLAUDE.md, docs, version notes, the Editor link and team settings, then a code audit and a step-by-step migration plan.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# Adopt the standards in an existing project

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

The project already works: change nothing in its code or assets without the user's approval.

## 1. Understand the project

Read `ProjectSettings/ProjectVersion.txt`, `Packages/manifest.json`, the folder structure, the assembly definitions, the scenes in the build, and any existing `CLAUDE.md`, `README.md` and `docs/`.

## 2. Set up Claude's side

These add files and don't touch code:

- `CLAUDE.md` from the [new-project template](../new-project/templates/CLAUDE.md), merged with what the existing file says. Record existing conventions that differ from the standards and must stay, such as the project's namespace scheme, under **Decisions**: they take precedence over the standards.
- The [documentation layout](../project-docs/SKILL.md), merged with the existing docs: `README.md` and `CLAUDE.md` as indexes, project knowledge in `docs/`, one topic per file. Move content instead of copying it, so each fact lives in one place.
- `docs/unity-version-notes.md`, as the [version notes guide](../version-notes/SKILL.md) describes.
- `.claude/settings.json` from the [team template](../new-project/templates/settings.json), merged with existing settings. It turns on loading the standards at the start of every session.
- The Editor link: `unity pipeline install --project-path <project>`, after asking, because it adds a package to the manifest.

Tell the user that the standards now load by themselves in every session of this project, and that `/unity-dev:standards off` turns that off.

## 3. Audit

Compare the project with the [code standards](../code-standards/SKILL.md), its [resource lifetimes](../code-standards/references/resource-lifetimes.md) rules, and the [performance guide](../performance/SKILL.md). Report findings grouped by impact, each with its location and the concrete fix:

1. **Correctness risks:** Unity null checks through interfaces, ScriptableObjects holding runtime state, catch-all blocks, fragile `WithParameter` registrations, static state that breaks Enter Play Mode without a domain reload, saves that a crash, a power loss or a killed background app can lose.
2. **Leaks:** subscriptions never disposed (MessagePipe, C# and static events, Input System callbacks), Addressables loads without a release, `CancellationTokenSource`s never disposed, `renderer.material` / `meshFilter.mesh` copies and other runtime-created objects never destroyed, native containers and GPU buffers never disposed, tweens never killed, pooled objects that don't reset on despawn.
3. **Performance:** per-frame allocations, `Update` methods on many objects, runtime `GetComponent` / `Find`, the default 30 fps on mobile, direct references that load all content, repeated objects drawn without batching.
4. **Architecture:** singletons and mutable statics, code in `Assembly-CSharp`, missing or cyclic assemblies, concrete cross-domain dependencies.
5. **Consistency:** naming, folders, typos in public or serialized names.

Read the code; don't guess from file names. Mention what already follows the standards.

## 4. Migration plan

Propose an order that keeps the project working after every step and gives the biggest benefit first: usually correctness risks and leaks, then performance, then assemblies and DI. Each step must be small enough to review and test on its own, and replace hand-written generic code with library modules where one exists. Start a step only after the user approves it.
