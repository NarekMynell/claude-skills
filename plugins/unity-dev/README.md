# unity-dev

Unity development: SOLID, interface-based architecture and C# standards with automated audits, a tested code library, new-project setup, performance, UI, audio, VFX, NPC behavior, 3D models and animation in Unity, version notes and a toolchain check. It brings core, game-design and modeling with it; a project switches off what it doesn't need, such as modeling in a 2D game.

Switch: `UNITY_DEV_STANDARDS`. Builds on core, game-design and modeling, and installs the official `unity` and `csharp-lsp` plugins. Requires the [Unity CLI](https://docs.unity.com/en-us/unity-cli) and the C# language server `csharp-ls` (`dotnet tool install --global csharp-ls`). Its hooks are bash scripts; on Windows they need Git Bash.

- With unity-dev on, when a turn ends, what changed is compared with the receipts the checks write in `docs/proofs/`: Claude is asked once to deal with those that fail, are out of date or don't exist, for the skills that are on.
- The code library is covered by 391 automated tests: 345 Edit Mode and 46 Play Mode, 23 of which check what the guides claim about VContainer, MessagePipe, UniTask and Unity. It compiles with no warnings on Unity 6000.6, and the Play Mode tests also pass in macOS and WebGL (IL2CPP) player builds (`dev/run-library-tests.sh`).
- Every C# example in the guides and module READMEs compiles against the real packages, and the audits that hold the musts (`ArchitectureAudit`, `UiAudit`, `SceneCostAudit`, `ColliderAudit`, `PacingAnalyzer`, `FootSlideMeter`) have a case for every defect they report.

## Install

```text
/plugin install unity-dev --marketplace NarekMynell/claude-skills
```

## Skills

<!-- catalog:skills -->
| Skill | Command | What it does | Switch |
|---|---|---|---|
| [adopt-standards](skills/adopt-standards/SKILL.md) | `/unity-dev:adopt-standards` | Brings an existing Unity project under the unity-dev standards without breaking it - CLAUDE.md, docs, version notes, the Editor link and team settings, then a code audit and a step-by-step migration plan. | `UNITY_DEV_SKILL_ADOPT_STANDARDS` |
| [animation](skills/animation/SKILL.md) | `/unity-dev:animation` | Plays character and animal animation in Unity without sliding - Humanoid import and retargeting, root motion settings, blend trees at measured speeds, foot IK for slopes and stairs, sockets and grips for held props, and Play Mode checks of foot sliding in the running game. | `UNITY_DEV_SKILL_ANIMATION` |
| [audio-design](skills/audio-design/SKILL.md) | `/unity-dev:audio-design` | Sound design and audio production for Unity games - the sound list per event, sources, escalating reward sounds, variation, AudioMixer groups and snapshots, ducking, and the audio service. | `UNITY_DEV_SKILL_AUDIO_DESIGN` |
| [code-standards](skills/code-standards/SKILL.md) | `/unity-dev:code-standards` | C# architecture and code standards for Unity - VContainer DI, domains and assemblies, MessagePipe, Providers, UniTask, DOTween, serialization and saving, configs, pooling, per-frame performance, naming and style. | `UNITY_DEV_SKILL_CODE_STANDARDS` |
| [library](skills/library/SKILL.md) | `/unity-dev:library` | The tested unity-dev code library - DI scopes and installers, Providers, pooling, state machines, startup flow, saving, audio, off-screen pausing, the architecture, UI and scene cost audits, pacing analysis, safe area, extensions, collections, algorithms - copied into a project under its own namespace. | `UNITY_DEV_SKILL_LIBRARY` |
| [models](skills/models/SKILL.md) | `/unity-dev:models` | Brings 3D models, characters and clips from Blender into Unity - the export settings Unity needs and what they give, import settings, Humanoid bones and avatars, URP materials, LOD groups, colliders with their audit, prefabs placed as instances, glTF at runtime, and checks in the Editor. | `UNITY_DEV_SKILL_MODELS` |
| [new-domain](skills/new-domain/SKILL.md) | `/unity-dev:new-domain` | Adds a feature area such as inventory, combat or shop to a unity-dev project - folder, assembly definition, installer in the scene scope, optional Logic and test assemblies, and the architecture doc entry. | `UNITY_DEV_SKILL_NEW_DOMAIN` |
| [new-project](skills/new-project/SKILL.md) | `/unity-dev:new-project` | Creates a new Unity game or app with the unity-dev standards - newest stable Editor, URP 3D, folder and assembly layout, the standard packages, DI root scope, Bootstrap scene, build profiles, docs and CLAUDE.md. | `UNITY_DEV_SKILL_NEW_PROJECT` |
| [npc-behavior](skills/npc-behavior/SKILL.md) | `/unity-dev:npc-behavior` | Makes people and animals behave naturally in the game world - reasons behind actions, rest and activity, varied timing, smooth steering with no sliding, crowds that don't walk through each other, groups and queues, species behavior, and how to check it in the running game on a phone budget. | `UNITY_DEV_SKILL_NPC_BEHAVIOR` |
| [performance](skills/performance/SKILL.md) | `/unity-dev:performance` | Unity performance as a top priority - budgets, frame rate per platform, stopping work off screen, baked light with no runtime cost, static objects, mobile URP settings, draw calls and batching, crowds, memory and build size, thermals, Web, profiling on device. | `UNITY_DEV_SKILL_PERFORMANCE` |
| [standards](skills/standards/SKILL.md) | `/unity-dev:standards` | Loads the unity-dev standards and guides - new projects, C# architecture and code rules, the tested code library, UI, performance, audio, VFX, NPC behavior, 3D models and animation in Unity, the done checklist - with core, game-design and modeling, and turns them on for every session in a Unity project. Add a task to start it right away; `off` and `on` switch every-session loading. | `UNITY_DEV_STANDARDS` |
| [toolchain](skills/toolchain/SKILL.md) | `/unity-dev:toolchain` | Checks, repairs and updates the Unity toolchain for Claude Code - Unity CLI, the Unity Pipeline package for live Editor control, the official Unity plugin, the C# language server. | `UNITY_DEV_SKILL_TOOLCHAIN` |
| [ui-quality](skills/ui-quality/SKILL.md) | `/unity-dev:ui-quality` | Designs and checks game UI that looks made for this game - concept from the game's world, tokens and component kit first, no template or AI look, corners and sprites done right, world markers, typography, automated UI audit, device-size reviews against references. | `UNITY_DEV_SKILL_UI_QUALITY` |
| [version-notes](skills/version-notes/SKILL.md) | `/unity-dev:version-notes` | Researches what changed in Unity between the versions Claude knows well and the project's version, and records what matters for the project in docs/unity-version-notes.md. | `UNITY_DEV_SKILL_VERSION_NOTES` |
| [vfx](skills/vfx/SKILL.md) | `/unity-dev:vfx` | Visual effects for Unity games - effect design and timing, no hard edges or visible masking, Particle System vs VFX Graph vs Shader Graph vs post-processing, overdraw, pooling, checks at gameplay speed. | `UNITY_DEV_SKILL_VFX` |
<!-- /catalog -->
