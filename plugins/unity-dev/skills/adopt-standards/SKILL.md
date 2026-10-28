---
name: adopt-standards
description: Brings an existing Unity project under the unity-dev standards without breaking it - adds CLAUDE.md, the documentation layout, version notes, the Unity CLI Editor link and team plugin settings, then audits the code against the standards and proposes a step-by-step migration. Use when the user wants to set up Claude, apply the standards or conventions, or audit architecture in a Unity project that already exists.
---

# Adopt the standards in an existing project

The project already works: change nothing in its code or assets without the user's approval.

## 1. Understand the project

Read `ProjectSettings/ProjectVersion.txt`, `Packages/manifest.json`, the folder structure, the assembly definitions, the scenes in the build, and any existing `CLAUDE.md`, `README.md` and `docs/`.

## 2. Set up Claude's side

These add files and don't touch code:

- `CLAUDE.md` from the `unity-dev:new-project` template ([templates/CLAUDE.md](../new-project/templates/CLAUDE.md)), merged with what the existing file says. Record existing conventions that differ from the standards and must stay, such as the project's namespace scheme, under **Standards** as decisions that take precedence.
- The documentation layout with `core:project-docs`, merging with existing docs.
- `docs/unity-version-notes.md` with `unity-dev:version-notes`.
- `.claude/settings.json` from the [team template](../new-project/templates/settings.json), merged with existing settings.
- The Editor link: `unity pipeline install --project-path <project>`, after asking, because it adds a package to the manifest.

## 3. Audit

Compare the project with `unity-dev:code-standards` and `unity-dev:performance`. Report findings grouped by impact, each with its location and the concrete fix:

1. **Correctness risks:** Unity null checks through interfaces, undisposed subscriptions, ScriptableObjects holding runtime state, catch-all blocks, fragile `WithParameter` registrations.
2. **Performance:** per-frame allocations, `Update` methods on many objects, runtime `GetComponent` / `Find`, the default 30 fps on mobile, direct references that load all content.
3. **Architecture:** singletons and mutable statics, code in `Assembly-CSharp`, missing or cyclic assemblies, concrete cross-domain dependencies.
4. **Consistency:** naming, folders, typos in public or serialized names.

Read the code; don't guess from file names. Mention what already follows the standards.

## 4. Migration plan

Propose an order that keeps the project working after every step and gives the biggest benefit first: usually correctness risks, then performance, then assemblies and DI. Each step must be small enough to review and test on its own, and replace hand-written generic code with library modules where one exists. Start a step only after the user approves it.
