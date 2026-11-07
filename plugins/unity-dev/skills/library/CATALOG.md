# Code library catalog

Every module, where it goes in a project's `Assets/_Project/Scripts/`, and what it needs. Details and examples: each module's `README.md` under `code/`. Tested, but not guaranteed free of bugs: review each file before copying it, as the [library guide](SKILL.md) describes.

Core modules share one assembly, `ProjectName.Core`, which references VContainer, UniTask and Addressables (`Unity.Addressables`, `Unity.ResourceManager`). A project that copies only some modules drops the references it doesn't need.

| Module | Destination | Provides | Depends on |
|---|---|---|---|
| Logging | `Core/Logging/` | `Log.Debug` compiled out of release builds; `Warning`, `Error`, `Exception` | — |
| Lifecycle | `Core/Lifecycle/` | `IPausable` | — |
| Extensions | `Core/Extensions/` | `IsAlive()`, `OrNull()`, `SafeDestroy()`, transform, vector, colour and list helpers | — |
| Collections | `Core/Collections/` | `MinHeap<TElement, TPriority>`, `RingBuffer<T>` | — |
| Algorithms | `Core/Algorithms/` | Shuffle, `WeightedPicker<T>`, `GridPathfinder` (A*), `GridFloodFill`, `SpatialHash<T>`, Poisson disk sampling | Collections, Extensions |
| Serialization | `Core/Serialization/`, `Core/Editor/Serialization/` | `SerializedInterface<T>`, `[SubclassSelector]`, `SerializableDictionary<TKey, TValue>`, `SceneReference` | — |
| Providers | `Core/Providers/` | `IProvider<T>`, `IProviderSetter<T>`, `Provider<T>`, `RegisterProvider<T>()` | Logging; VContainer |
| StateMachines | `Core/StateMachines/` | `StateMachine<TState>`, `AsyncStateMachine<TState>` | UniTask |
| DI | `Core/DI/` | `ModularLifetimeScope`, `ScopeInstaller`, `IFactory<T>`, `ComponentFactory<T>`, `GlobalResolver` | VContainer |
| Pooling | `Core/Pooling/` | `ComponentPool<T>`, `PrefabPoolRegistry`, `IPoolable` | DI, Extensions; VContainer |
| Scenes | `Core/Scenes/` | `ISceneLoader`, `SceneLoader`, `ISceneTransition`, `NoSceneTransition` | UniTask |
| Bootstrap | `Core/Bootstrap/`, `Core/Editor/Bootstrap/` | `IBootstrapStep`, `BootstrapFlow`, `BootstrapProgress`, `FrameRateStep`, `LoadFirstSceneStep`, Play from Bootstrap | Providers, Scenes, Serialization, Logging; VContainer, UniTask |
| ContentLoading | `Core/ContentLoading/` | `IContentLoader`, `AddressablesContentLoader` | Addressables, UniTask; VContainer |
| Culling | `Core/Culling/` | `IVisibilityPauser` (one CullingGroup for all targets), `PauseWhenHidden`, `RegisterVisibilityPauser()`, `MovementProbe` | Lifecycle, Extensions, Logging; VContainer |
| Motion | `Core/Motion/` | `FootSlideMeter`, `Gait`, `CrowdOverlapMeter`, `ActivityShares`: foot sliding, speed and cadence against the body, actors inside each other and how actors spend their time, measured in the running game | — |
| Proofs | `Core/Proofs/` | `ProofReceipt`: a check records its last run in `docs/proofs/` | — |
| Architecture | `Core/Editor/Architecture/`, `Core/Tests/Architecture/` | `ArchitectureAudit` and `ProjectArchitectureTests`: fails the test run on violations of the architecture rules. In every project | Proofs |
| UiChecks | `Core/Editor/UiChecks/` | `UiAudit`, `UiAuditSettings`, `UssTokenAudit`: capsules, stretched sprites, the project's radius and type scales, overflow, touch targets. In every project with UGUI | Proofs, UI; `UnityEngine.UI`, `Unity.TextMeshPro` |
| CostChecks | `Core/Editor/CostChecks/` | `SceneCostAudit`, `NeverMovedProbe`: realtime light, missing static flags, work off screen. `ColliderAudit`: colliders past or away from the model or closing what it leaves open, a character off its feet, walls that stop nothing | Proofs, Culling |
| UI | `Core/UI/` | `SafeArea`, `IUiShape` | — |
| Persistence | `Persistence/` | `ISaveService<T>`, `ISaveStorage`, `SaveSchema<T>`, `ISaveMigration`; `RegisterJsonSave<T>()` and `RegisterFileSaveStorage()` for versioned JSON saves in crash-safe files | Newtonsoft JSON, UniTask; VContainer |
| Audio | `Audio/` | `AudioCue`, `IAudioService` with `RegisterAudio()`, `AudioVolume` | Pooling, DI, Extensions, Logging; VContainer |
| Pacing | `Pacing/` | `PacingAnalyzer`: pacing measures and findings from a balance simulation's timelines, with no engine references | — |

Tests: `Core/Tests/` (Edit Mode), `Core/Tests/PlayMode/`, `Persistence/Tests/`, `Persistence/Tests/PlayMode/`, `Audio/Tests/`, `Pacing/Tests/`. Copy the tests of every module you take. Play Mode tests also run in players: run them in a development build of every target platform, because file systems, threading (none on Web) and IL2CPP differ from the Editor.
