---
name: library
description: The tested unity-dev code library - DI scopes and installers, Providers, pooling, state machines, startup flow, saving, audio, safe area, extensions, collections, algorithms - copied into a project under its own namespace.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# Code library

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

Ready building blocks written to the [code standards](../code-standards/SKILL.md) and covered by tests. The library is a source to copy from, not a dependency: a project takes only what it needs, and the copied code becomes the project's own code, in its own namespace, free to change.

**The code can still contain bugs or fall behind the project's package versions.** Tests reduce that risk; they don't remove it. Reviewing every file before it enters a project is part of using a module, not an option.

[CATALOG.md](CATALOG.md) lists every module: what it does, where it goes in a project, and what it needs. Read it before writing generic code. When a module covers the need, start from it instead of writing the code again.

## Layout

[code/](code/), next to this file, mirrors a project's `Assets/_Project/Scripts/` folder, written with the placeholder prefix `Company.Product`:

- `code/Core/<Module>/`: generic building blocks, in the `Company.Product.Core` assembly;
- `code/<Domain>/`: ready domains, such as Audio or Persistence, each with its own assembly.

Every module folder has a `README.md`: purpose, API with a short example, dependencies (other modules, packages, defines) and setup steps.

## Using a module

1. Read the module's README. Take its module dependencies too.
2. **Review the code** as you would a colleague's pull request, before copying it: correctness, resource lifetimes ([rules](../code-standards/references/resource-lifetimes.md)), cancellation, edge cases, allocations. Check every package API it calls against the project's installed version (`Packages/packages-lock.json`; the source is in `Library/PackageCache/`). Fix what you find in the project's copy, and tell the user, so the library gets the fix too.
3. Copy its `.cs` files and its tests to the same relative path under the project's `Assets/_Project/Scripts/`, plus the assembly definitions and `AssemblyInfo.cs` the project doesn't have yet. The README stays in the library. Unity generates the `.meta` files.
4. Replace every occurrence of `Company.Product` with the project's prefix (from `CLAUDE.md`), string literals included: namespaces, `using` directives, assembly definitions, `InternalsVisibleTo`, menu paths (`Tools/…`, `CreateAssetMenu`) and settings keys. If a file goes to a different folder, its namespace follows that folder.
5. Merge into the project's assemblies: files for `Core` join the project's existing Core assembly, with any missing references added. Never create a second Core assembly.
6. Adapt the code to the project: keep what it needs, remove what it doesn't, extend it.
7. Copy the module's tests into the matching test assembly. The project compiles with no errors or warnings, and the tests pass there: Edit Mode and Play Mode in the Editor, and the Play Mode tests in a development build of each target platform too. File systems, threading (none on Web) and IL2CPP differ from the Editor.
8. List the copied modules in `docs/architecture.md` with the unity-dev version (from [plugin.json](../../.claude-plugin/plugin.json)), so a later library fix can be compared with the project's copy and ported.

## Updating a project's copy

The copy doesn't update with the plugin. When the user asks, or when a task touches a copied module:

1. Read the unity-dev version recorded for the module in `docs/architecture.md`.
2. Read the entries newer than it in [CHANGES.md](CHANGES.md) for the copied modules.
3. Port every **Fix**, and the **Changes** the project wants, into the project's copy. The copy may have diverged: merge the change into it, keeping the project's own edits, instead of overwriting the file.
4. Run the module's tests as in step 7, then record the new version.

## Growing the library

Generic code written in a project, code that knows nothing about the project and would help others, is a library candidate. Tell the user, so it can be added. Authoring rules: [references/authoring.md](references/authoring.md).
