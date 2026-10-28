# <Product name>

<What the game or app is, in one or two sentences.> Unity <version>, URP, targets <platforms>.

## Standards

This project follows the unity-dev standards. Decisions recorded in this file and in `.claude/rules/` take precedence over them.

- Before writing or reviewing C#, load `unity-dev:code-standards`.
- Before writing generic code, check the code library with `unity-dev:library`.
- Load the matching skill before the work: UI `unity-dev:ui-quality`, performance `unity-dev:performance`, sounds `unity-dev:audio-design`, effects `unity-dev:vfx`, game design `unity-dev:game-design`, 3D models `blender:game-assets`.
- Drive the open Editor through the Unity CLI (`unity status`, `unity command`) instead of hand-editing scene, prefab or asset files.
- Assembly prefix: `<Company>.<Product>`.

## Before reporting a task as done

1. **Correct.** No errors or warnings from the C# language server or the Unity console. Checked in Play Mode where the change is visible.
2. **Best solution.** Nothing simpler or better; it scales with the expected growth without over-engineering.
3. **Architecture.** Right domain and assembly, dependency direction, DI instead of statics, interfaces where they belong.
4. **Performance.** No per-frame allocations or needless work; draw calls and memory within `docs/performance-budgets.md`.
5. **Robust.** Destroyed objects, cancellation, disposed subscriptions, errors.
6. **Consistent.** Naming and structure rules followed; docs updated.

If a check fails, fix it before moving on.

## Documentation

- Project knowledge lives in `docs/`, instructions for Claude in this file and in `.claude/rules/`. Read this index, then open only what the task needs.
- A change that affects documented behavior updates the matching `docs/` file in the same change. Adding, renaming or removing a file updates this index and the one in `README.md`.

| File | Read when |
|---|---|
| `docs/architecture.md` | Adding or changing a domain, scope, installer or startup step |
| `docs/unity-version-notes.md` | Using an engine API or feature that may have changed in recent Unity versions |
