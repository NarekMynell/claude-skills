---
name: new-project
description: Creates a new Unity game or app with the unity-dev standards - newest stable Editor, URP 3D, folder and assembly layout, the standard packages, DI root scope, Bootstrap scene, build profiles, docs and CLAUDE.md.
disable-model-invocation: true
argument-hint: "[game idea]"
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# New Unity project

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

Run the guided flow of the official `unity:new-unity-project` skill (concept → platforms and monetization → Editor install in the background → project and source control → packages → first commit → monetization handoff), with the defaults and additions below. Where they differ, this skill wins. Command syntax lives in `unity:unity-cli` and `unity:unity-package-management`; don't guess it.

## Defaults

Fill in every setting the user didn't specify.

**Editor version: the newest stable release.** Stable means a final (`f`) release from the LTS, Supported or Tech stream; ignore alpha and beta. LTS is not required.

1. Newest stable installed: `unity editors --installed --format json`.
2. Newest stable available: `unity releases --format json`.
3. If a newer stable release exists, recommend it and list what it improves over the installed one, from its release notes. The user decides whether to download it.
4. Otherwise, or if the user declines, use the newest stable installed version.

**Render pipeline:** URP. **Mode:** 3D. **Template:** Universal 3D, `com.unity.template.urp-blank`; confirm the id with `unity templates list --editor <version> --type core`.

**Source control:** Git with LFS for binary assets (the official flow's `--git-lfs`), unless the user chooses Unity Version Control.

## Setup after the project is created

Do these between the official flow's package step and its first commit. Work in the running Editor through the Unity CLI wherever possible.

1. **Editor link.** `unity pipeline install --project-path <project>`, open the project, and wait for `unity status` to report `ready`.
2. **Folders.** Create the `Assets/_Project/` layout from the [code organization](../code-standards/references/code-organization.md) rules. Only folders that receive content now.
3. **Trim the template.** Remove packages the brief doesn't need (Visual Scripting, Multiplayer Center, Collab, and similar) through the Client API.
4. **OpenUPM registry.** Add it to `Packages/manifest.json`; the Client API has no call for registries:
   ```json
   "scopedRegistries": [
     { "name": "OpenUPM", "url": "https://package.openupm.com", "scopes": ["jp.hadashikick", "com.cysharp"] }
   ]
   ```
5. **Standard packages** through the Client API, each pinned to an exact version: for Unity packages the version the Package Manager recommends for this Editor (`versions.recommended`, else `latestCompatible`), for OpenUPM packages the newest release. `jp.hadashikick.vcontainer`, `com.cysharp.unitask`, `com.cysharp.messagepipe`, `com.cysharp.messagepipe.vcontainer`, `com.unity.addressables`, and `com.unity.inputsystem` unless the template already has it. Add `com.unity.nuget.newtonsoft-json` when the Persistence module is installed.
6. **DOTween** is in no package registry. Ask the user to add the free DOTween from the Asset Store (Package Manager > My Assets) into `Assets/Plugins/Demigiant/`. Then: DOTween Utility Panel > **Setup DOTween**, then **Create ASMDEF** (asmdef code can't reference `Assembly-CSharp-firstpass`), and add the scripting define `UNITASK_DOTWEEN_SUPPORT` (UniTask detects DOTween only when it is a UPM package). DOTween keeps its settings asset in a `Resources` folder, the one exception to the code standards' rule.
7. **VContainer source generator**, as in the [DI reference](../code-standards/references/dependency-injection.md#source-generator).
8. **Code library:** copy the DI and Bootstrap modules, with the modules they depend on, into the project as the [code library](../library/SKILL.md) describes.
9. **DI root.** Create the root `ModularLifetimeScope` prefab under `Assets/_Project/Prefabs/` and the `VContainerSettings` asset under `Assets/_Project/Settings/`, and assign the prefab as the root. An asset created by script must be added to **Preloaded Assets** (`PlayerSettings.SetPreloadedAssets`), or VContainer never finds it; check that it's listed. Register MessagePipe in the root scope as the [DI reference](../code-standards/references/dependency-injection.md#messagepipe-registration) shows.
10. **Bootstrap scene.** `Assets/_Project/Scenes/Bootstrap.unity`: a camera, a loading screen with tiny assets, and the startup flow from the Bootstrap module. It is build index 0. Turn on the module's Play-from-Bootstrap mode, so Play in the Editor runs the same startup as a build.
11. **Project settings:**
    - Active Input Handling: Input System Package.
    - Frame rate and quality are set by the Bootstrap module's frame-rate step; configure it for the target platforms ([performance](../performance/SKILL.md)).
    - **No domain reload on entering Play Mode** (Project Settings > Editor > Enter Play Mode Settings): Unity 6.6's default, and what Unity recommends. The project's own code holds no static state, and any static a package needs reset is handled as the [resource lifetimes](../code-standards/references/resource-lifetimes.md#static-state-and-enter-play-mode) reference describes. Check that entering Play Mode twice in a row behaves exactly like the first run. If a package breaks without the reload, turn it on and record why in `docs/architecture.md`.
12. **Build profiles.** One per target platform, plus development and release variants where their settings differ (development build, defines, logging, stripping). Bootstrap is scene 0 in each. Release builds use IL2CPP and the highest stripping level the project tolerates, with `link.xml` for the types used through reflection, such as save DTOs; Android release builds target ARM64. VContainer Diagnostics is off in release builds. Commit the profiles.
13. **Documentation**, in the [documentation layout](../project-docs/SKILL.md). Concise, one topic per file, linked instead of duplicated, no empty placeholders:
    - `README.md`: what the project is, its requirements (Unity version, assets imported by hand such as DOTween), how to open and run it, one line per `docs/` file;
    - `CLAUDE.md` from [templates/CLAUDE.md](templates/CLAUDE.md), filled in from the brief;
    - `docs/architecture.md`: domains, scopes, startup steps;
    - `docs/unity-version-notes.md`, as the [version notes guide](../version-notes/SKILL.md) describes;
    - `docs/performance-budgets.md` when the target devices are known.
14. **Team setup.** Copy [templates/settings.json](templates/settings.json) to `.claude/settings.json`: it registers this marketplace with auto-update, lists the plugins the project expects, and turns on loading the standards at the start of every session (`UNITY_DEV_STANDARDS`, with the rule that lets those sessions read the plugin's guides). Committing it installs nothing; tell the user that each teammate runs `claude plugin install unity-dev@narek-skills --scope project` once, after trusting the folder (dependencies come with it). Add `.claude/settings.local.json` to `.gitignore`.
15. **Verify.** No errors or warnings in the console. Play from Bootstrap reaches the first scene. `unity status` is `ready`.

Then make the official flow's first commit.

## Report

Project path, Editor version, template, installed packages with versions, library modules copied, what the user still has to do (for example importing DOTween), and the next step. Tell the user that the standards load by themselves in every session started in the project folder, and that `/unity-dev:standards off` turns that off.
