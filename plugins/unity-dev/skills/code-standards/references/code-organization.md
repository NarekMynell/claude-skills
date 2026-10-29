# Code organization

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

## Project layout

```
Assets/
├── _Project/               This project's own code and assets. The underscore keeps it on top.
│   ├── Scripts/
│   │   ├── App/            Composition root: root scope, startup flow, app-wide setup
│   │   ├── Core/           Generic building blocks with no knowledge of game features
│   │   └── <Domain>/       One feature area per folder
│   ├── Art/
│   ├── Audio/
│   ├── Configs/            ScriptableObject config assets, one subfolder per domain
│   ├── Prefabs/
│   ├── Scenes/
│   └── Settings/           Render pipeline, input and other project assets
├── Plugins/                Third-party code and native plugins
└── ...                     Folders that packages and imported assets create stay where they install
```

Core is one assembly, `<Company>.<Product>.Core`, with `Core.Editor` and `Core.Tests` beside it. Something enters Core only if it knows nothing about game features and either two domains need it or it is clearly generic. Much of it is copied from the [code library](../../library/SKILL.md) and then belongs to the project.

## Inside a domain

```
Combat/
├── <Company>.<Product>.Combat.asmdef
├── CombatInstaller.cs      DI registrations of this domain
├── IDamageService.cs       Contracts and services at the root
├── DamageService.cs
├── Configs/                ScriptableObject config classes
├── Messages/               MessagePipe message types
├── States/                 State types held by Providers
├── Views/                  MonoBehaviours
└── Editor/                 Editor-only code, own assembly
```

A large domain splits into subfeature folders (`Interaction/Selection/`), each with the same internal layout. Create a folder only when it has content.

## Assembly definitions

Reference assemblies by name: readable in reviews, and copied code keeps working without its `.meta` files. Unity also offers GUID references, which survive renames; with names, renaming an assembly means updating its references, and the compiler reports each one. Every assembly sets `autoReferenced: false`.

Runtime:

```json
{
    "name": "Acme.Shooter.Combat",
    "rootNamespace": "Acme.Shooter.Combat",
    "references": [
        "Acme.Shooter.Combat.Logic",
        "VContainer",
        "UniTask",
        "MessagePipe"
    ],
    "autoReferenced": false
}
```

Logic without Unity (`noEngineReferences` makes the compiler reject any `UnityEngine` use):

```json
{
    "name": "Acme.Shooter.Combat.Logic",
    "rootNamespace": "Acme.Shooter.Combat.Logic",
    "references": [],
    "autoReferenced": false,
    "noEngineReferences": true
}
```

Editor:

```json
{
    "name": "Acme.Shooter.Combat.Editor",
    "rootNamespace": "Acme.Shooter.Combat.Editor",
    "references": [
        "Acme.Shooter.Combat"
    ],
    "includePlatforms": [
        "Editor"
    ],
    "autoReferenced": false
}
```

Edit Mode tests (for Play Mode tests, use an empty `includePlatforms`):

```json
{
    "name": "Acme.Shooter.Combat.Tests",
    "rootNamespace": "Acme.Shooter.Combat.Tests",
    "references": [
        "UnityEngine.TestRunner",
        "UnityEditor.TestRunner",
        "Acme.Shooter.Combat",
        "Acme.Shooter.Combat.Logic"
    ],
    "includePlatforms": [
        "Editor"
    ],
    "overrideReferences": true,
    "precompiledReferences": [
        "nunit.framework.dll"
    ],
    "autoReferenced": false,
    "defineConstraints": [
        "UNITY_INCLUDE_TESTS"
    ]
}
```

## Third-party assemblies

- VContainer, UniTask and MessagePipe ship asmdefs: reference them by name (`VContainer`, `UniTask`, `MessagePipe`, `MessagePipe.VContainer`). UniTask's integrations are separate assemblies: `UniTask.DOTween` for awaiting tweens, `UniTask.Addressables` for awaiting Addressables handles. Addressables code references `Unity.Addressables` and `Unity.ResourceManager`.
- DOTween is a precompiled DLL plus source modules in `Assets/Plugins/Demigiant/`. Source in a `Plugins` folder compiles into `Assembly-CSharp-firstpass`, which an asmdef can't reference. Create DOTween's asmdef once (DOTween Utility Panel → **Create ASMDEF**) and reference `DOTween.Modules`.

## Shared contracts

When two domains need each other's contracts, move the interfaces, messages and state types into a lower assembly named for what it holds (`Acme.Shooter.Combat.Contracts`), referenced by both. Never solve a cycle with a global or a service locator.
