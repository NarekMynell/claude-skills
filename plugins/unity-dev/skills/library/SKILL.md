---
name: library
description: The unity-dev code library - ready, tested C# building blocks for Unity projects (DI scopes and installers, Providers, pooling, state machines, startup flow, saving, audio service, safe area, extensions, collections, algorithms and more), copied into a project under the project's own namespace. Use before writing generic code in a Unity project, and whenever a ready implementation of a common system would help.
---

# Code library

Ready building blocks written to `unity-dev:code-standards` and covered by tests. The library is a source to copy from, not a dependency: a project takes only what it needs, and the copied code becomes the project's own code, in its own namespace, free to change.

[CATALOG.md](CATALOG.md) lists every module: what it does, where it goes in a project, and what it needs. Read it before writing generic code. When a module covers the need, start from it instead of writing the code again.

## Layout

`${CLAUDE_PLUGIN_ROOT}/skills/library/code/` mirrors a project's `Assets/_Project/Scripts/` folder, written with the placeholder prefix `Company.Product`:

- `code/Core/<Module>/`: generic building blocks, in the `Company.Product.Core` assembly;
- `code/<Domain>/`: ready domains, such as Audio or Persistence, each with its own assembly.

Every module folder has a `README.md`: purpose, API with a short example, dependencies (other modules, packages, defines) and setup steps.

## Using a module

1. Read the module's README. Take its module dependencies too.
2. Copy its `.cs` files and its tests to the same relative path under the project's `Assets/_Project/Scripts/`, plus the assembly definitions and `AssemblyInfo.cs` the project doesn't have yet. The README stays in the library. Unity generates the `.meta` files.
3. Replace `Company.Product` with the project's prefix (from `CLAUDE.md`) in namespaces, `using` directives and assembly definitions. If a file goes to a different folder, its namespace follows that folder.
4. Merge into the project's assemblies: files for `Core` join the project's existing Core assembly, with any missing references added. Never create a second Core assembly.
5. Adapt the code to the project: keep what it needs, remove what it doesn't, extend it.
6. Copy the module's tests into the matching test assembly. The project compiles with no errors or warnings, and the tests pass.
7. List the copied modules in `docs/architecture.md` with the unity-dev version (from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`), so a later library fix can be compared with the project's copy and ported.

## Growing the library

Generic code written in a project, code that knows nothing about the project and would help others, is a library candidate. Tell the user, so it can be added. Authoring rules: [references/authoring.md](references/authoring.md).
