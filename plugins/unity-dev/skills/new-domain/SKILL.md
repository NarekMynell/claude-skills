---
name: new-domain
description: Adds a new domain (feature area) to a Unity project that follows the unity-dev standards - folder, assembly definition, installer registered in the scene scope, optional Logic and test assemblies, and the architecture doc entry. Use when the user wants a new feature area, system, module or domain such as inventory, combat, shop, quests or audio.
---

# New domain

## Decide

1. **Name.** One PascalCase noun for the feature area (`Inventory`, `Combat`). Never `Application`, never `Utils`, `Common` or `Manager`.
2. **Does it belong in the library instead?** If it knows nothing about this project and is generic, it is a library module, not a domain (`unity-dev:library`).
3. **Dependencies.** List the domains it needs. Each dependency must be one-way. If two domains would need each other, plan the shared contracts assembly first.
4. **Assembly prefix.** Read `<Company>.<Product>` from `CLAUDE.md`, or from an existing project assembly.

## Create

Follow the layout and asmdef templates in [code organization](../code-standards/references/code-organization.md):

1. `Assets/_Project/Scripts/<Domain>/` with `<Company>.<Product>.<Domain>.asmdef` referencing only what the domain uses.
2. `<Domain>Installer : ScopeInstaller` registering the domain's services, with its config and scene references as serialized fields.
3. Subfolders only for what exists now: `Configs/`, `Messages/`, `States/`, `Views/`, `Editor/`.
4. A `.Logic` assembly with `noEngineReferences: true` when the domain has substantial logic.
5. `<Company>.<Product>.<Domain>.Tests` with at least one test of the domain's main behavior.
6. Add the installer to the scene's `ModularLifetimeScope` installer list, in dependency order (or to the root scope's list for an app-wide domain).
7. Add the domain to `docs/architecture.md`: its purpose, its dependencies, and its scope.

## Verify

The project compiles with no errors or warnings, the tests pass, and entering Play Mode resolves the domain's services without VContainer exceptions.
