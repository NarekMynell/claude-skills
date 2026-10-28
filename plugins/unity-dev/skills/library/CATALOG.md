# Code library catalog

Every module, where it goes in a project's `Assets/_Project/Scripts/`, and what it needs. Details and examples: each module's `README.md` under `code/`.

Core modules share one assembly, `Company.Product.Core`, which references VContainer, UniTask, `UniTask.Addressables`, Addressables (`Unity.Addressables`, `Unity.ResourceManager`). A project that copies only some modules drops the references it doesn't need.

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
| Culling | `Core/Culling/` | `VisibilityPauser` (CullingGroup driver) | Lifecycle |
| UI | `Core/UI/` | `SafeArea` | — |
| Persistence | `Persistence/` | `ISaveService<T>`, `JsonSaveService<T>`, `ISaveMigration`, `SaveSchema<T>`, `ISaveStorage`, `FileSaveStorage` | Newtonsoft JSON, UniTask; VContainer |
| Audio | `Audio/` | `AudioCue`, `IAudioService`, `AudioService`, `AudioVolume` | Pooling, DI, Extensions, Logging; VContainer |

Tests: `Core/Tests/` (Edit Mode), `Core/Tests/PlayMode/`, `Persistence/Tests/`, `Audio/Tests/`. Copy the tests of every module you take.
