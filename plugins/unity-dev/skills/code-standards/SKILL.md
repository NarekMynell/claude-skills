---
name: code-standards
description: C# architecture and code standards for Unity - VContainer DI, domains and assemblies, MessagePipe, Providers, UniTask, DOTween, serialization and saving, configs, pooling, per-frame performance, naming and style.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# Unity C# standards

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

These rules apply to new and changed code. In an existing project that doesn't follow them yet, apply them to the code you write, and refactor existing code only when the user asks. Decisions recorded in the project's `CLAUDE.md` or `.claude/rules/` take precedence.

Generic building blocks named below (`IsAlive()`, Providers, pools, installers, the state machine) come from the code library: copy them into the project's Core from the [code library](../library/SKILL.md) instead of writing them again.

## Architecture

- **SOLID.** Interfaces are the main design tool. A class depends on interfaces, never on another domain's concrete classes.
- **Composition over inheritance.** Inherit only for a true is-a relationship with shared behavior, and keep hierarchies shallow: one abstract base and its implementations.
- **Role interfaces.** An object implements only the capabilities it has: `IClickable`, `IDamageable`. Input arrives through Unity's EventSystem interfaces and the Input System; role interfaces say what the input means in the game.
- **Cohesive interfaces.** One interface per role, not per method. Operations that always come together stay together (`IPausable` has `Pause()` and `Resume()`). Split where consumers differ: read access and write access are separate interfaces.
- **Every abstraction needs a reason:** a DI service, a domain boundary, more than one implementation, or a test seam. Services always sit behind an interface. Data types, views and configs don't need one.
- **Single responsibility** for every class, component and method. A method does one thing at one level of abstraction.
- **No singletons, no mutable static state.** Static is allowed only for stateless code: extension methods, pure helpers, constants, cached IDs (`static readonly int SpeedId = Animator.StringToHash("Speed")`). This also keeps Enter Play Mode without domain reload safe.
- **Logic in plain C#, Unity at the edges.** Game logic lives in plain C# classes registered in DI. MonoBehaviours are thin views and adapters: they display state, forward input and hold scene references.
- **Unity null.** An interface reference doesn't see Unity's destroyed state: after its MonoBehaviour is destroyed, `IDamageable damageable` is still non-null and `damageable?.TakeDamage()` calls into a destroyed object. When an interface can point to a `UnityEngine.Object`, check it with `IsAlive()`, or call through `OrNull()?.`, never with `== null`, `?.` or `??` on the reference itself.
- **Completion is awaited.** An operation that finishes later returns a `UniTask`. Don't signal completion with `OnCompleted` events: awaiting carries exceptions and cancellation, events don't.
- **State machines** model behavior with a clear set of modes: app flow, character behavior, screens. Use the library's StateMachines module.

## Code organization

Full layout, asmdef templates and examples: [references/code-organization.md](references/code-organization.md).

- Project code lives in `Assets/_Project/Scripts/`: `App/` is the composition root, `Core/` holds generic building blocks with no knowledge of game features (many of them copied from the code library), and `<Domain>/` holds one feature area each.
- **A domain is one feature area with its own asmdef:** `Combat`, `Inventory`, `UI`, `Audio`, `Persistence`. App composes domains and contains no game logic. Name it `App`, never `Application`: a namespace segment named `Application` hides `UnityEngine.Application`.
- **Assembly names** are `<Company>.<Product>.<Domain>`. `rootNamespace` equals the assembly name, and namespaces mirror the folder path. No code stays in `Assembly-CSharp`.
- **Dependency direction:** App → domains → Core → third-party. Core never references a domain. A domain references another domain only when the dependency is real and one-way. When two domains need each other, move the shared contracts (interfaces, messages, states) into a lower assembly.
- **Encapsulation.** Implementations are `internal`. Only contracts other assemblies use are `public`. The installer registers internal implementations under public interfaces.
- `autoReferenced: false` on every assembly, so Unity's predefined assemblies (`Assembly-CSharp`) can't use it and every dependency is a declared reference. Only assemblies that use a third-party package reference it.
- A logic-heavy domain moves its logic into `<Company>.<Product>.<Domain>.Logic` with `noEngineReferences: true`: the compiler then guarantees it has no Unity dependency, and its tests are plain Edit Mode tests with no scene or Play Mode.
- Editor code goes in `<Domain>/Editor/` with an Editor-only assembly. Inside a `….Editor` namespace the name `Editor` means that namespace: derive custom inspectors from `UnityEditor.Editor`. Tests go in `<Company>.<Product>.<Domain>.Tests`, Edit Mode unless they need the runtime.
- One type per file, file name equals type name.

## Dependency injection

VContainer for all DI. Patterns and code: [references/dependency-injection.md](references/dependency-injection.md).

- Plain C# classes get dependencies through the constructor. MonoBehaviours get them through an `[Inject]` method named `Construct`, which only stores them ([resource lifetimes](references/resource-lifetimes.md#where-to-release)). No `FindObjectOfType`, no service locator lookups.
- **Scopes.** The root scope holds app-wide services (saving, audio, settings, scene loading, analytics). It is a prefab assigned in `VContainerSettings`, so VContainer creates it with the first scene, keeps it across scene loads and parents every scene scope to it. Scene scopes hold scene services.
- **Domain installers.** A scene has one `ModularLifetimeScope`. Each domain contributes one `ScopeInstaller` that registers only that domain's services and holds its scene and config references. The scope lists its installers in the Inspector and runs them in that order.
- **Runtime creation** goes through an injected typed factory that instantiates with `IObjectResolver.Instantiate` and returns the component or interface the caller needs. Never `Object.Instantiate` an object that needs injection. The factory lives in the scope that owns what it creates, or gives every instance a parent: the root scope's resolver alone marks new objects `DontDestroyOnLoad`. The caller owns what a factory returns.
- **Scene objects** are serialized on the installer and registered with `RegisterComponent`. Objects that only receive injection are listed in the scope's **Auto Inject Game Objects**, or injected with `builder.RegisterBuildCallback(c => c.InjectGameObject(view.gameObject))`. No `RegisterComponentInHierarchy`: it searches the scene.
- **Configs** are registered with `RegisterInstance` and injected into services. ScriptableObjects never receive injection.
- **Entry points.** `RegisterEntryPoint<T>` with `IStartable`, `ITickable`, `IFixedTickable`, `ILateTickable`, `IAsyncStartable` and `IDisposable` replaces MonoBehaviour lifecycle methods for services.
- **Typed configuration.** Pass service settings as a typed config object. Never `WithParameter("name", value)`: a rename breaks it silently at runtime.
- **No reflection.** The VContainer source generator must be installed (see the reference). Without it, VContainer injects through reflection.
- **Global resolver** only as a last resort for code DI can't reach. One static access point, cleared when its scope is disposed, and a comment at every use explaining why DI couldn't be used. `GlobalMessagePipe` is set by the root scope, because the MessagePipe diagnostics window needs it ([DI reference](references/dependency-injection.md#messagepipe-registration)); code uses it under the same rule.

## Communication between systems

Details and Provider code: [references/messaging-and-state.md](references/messaging-and-state.md).

| Mechanism | Use when |
|---|---|
| MessagePipe message | Something happened or is requested, and the sender doesn't know who reacts. The default between domains. |
| Provider (`IProvider<T>`) | Others need a current value and its changes. |
| Direct call through an interface | The caller knows who does the work. Prefer it over a message when the receiver is known. |
| C# `event` / `Action` | A child notifies its owner, or a one-to-one callback inside a domain. |
| `UnityEvent` | Wiring set up in the Inspector, and Unity UI component callbacks. |
| `UniTask` | Waiting for an operation to finish. |

- Never `SendMessage`, `BroadcastMessage` or string-named events.
- **Messages** are `readonly struct`s in the owning domain's `Messages/` folder. Events use the past tense (`LevelCompleted`), requests end in `Request` (`SelectionRequest`).
- **Every subscription is disposed:** collected in a `DisposableBag` disposed in `Dispose()` / `OnDestroy()`, or bound with `.AddTo(destroyCancellationToken)`. Messages carry values, never ownership of disposables, pooled objects or Unity objects.
- Buffered publishers only for late subscribers that need the last message. Shared state that others read is a Provider.
- **Provider state types** are a dedicated `readonly struct` per concept (`SelectionState`) that implements `IEquatable<T>`. Never a primitive or a shared type: there is one Provider per type, so `IProvider<bool>` would be shared by everyone.

## Async

- **UniTask for all async code.** No coroutines: they can't return values, don't pass exceptions to the caller, can't be cancelled cleanly and allocate. No `Awaitable`: one async type across the codebase.
- **Cancellation.** Every async method takes a `CancellationToken` as its last parameter and passes it down. MonoBehaviours use `destroyCancellationToken`. Services cancel and then dispose their own `CancellationTokenSource` in `Dispose()`; every source, linked ones included, is disposed. Timeouts use `CancelAfterSlim`.
- **Cancellation isn't an error.** `OperationCanceledException` propagates; it is caught only at the top of a chain, to stop quietly, and never logged as an error.
- **No `async void`.** Fire-and-forget is `async UniTaskVoid` with `.Forget()`, only at the top of a call chain, with exceptions logged.
- **A `UniTask` is awaited once.** Use `.Preserve()` to share one.
- **Threads.** Unity APIs only on the main thread. Work that touches no Unity object can move to the thread pool (`UniTask.RunOnThreadPool`), except on Web, which has no threads.
- **Waiting for a condition:** await the event that makes it true (`UniTaskCompletionSource`, a message, a Provider value). Don't poll with `while (!ready) await UniTask.Yield()`.
- Independent operations run in parallel with `UniTask.WhenAll`.
- Choose delay timing on purpose: UI that keeps working while the game is paused uses unscaled time.

## Tweening and animation

- DOTween for code-driven motion (UI, transforms, materials, camera). Animator for authored skeletal animation. Timeline for hand-animated sequences and cutscenes.
- DOTween is initialized once at startup with a capacity that matches the project's peak (`DOTween.Init().SetCapacity(...)`), so it never resizes at runtime.
- Reused animations are built once with `SetAutoKill(false)`, replayed with `Restart()`, and killed by their owner.
- Every tween is tied to its owner with `SetLink(gameObject)` or killed in `OnDestroy()` / `Dispose()`; on pooled objects, in `OnDespawned`.
- Await tweens with `await tween.ToUniTask(TweenCancelBehaviour.KillAndCancelAwait, ct)`, and `SetAutoKill(false)` tweens with `AwaitForComplete(TweenCancelBehaviour.CancelAwait, ct)`: the default `Kill` ends the await normally on cancellation, and `ToUniTask` waits for the kill ([details](references/resource-lifetimes.md#tweens)). This needs the `UNITASK_DOTWEEN_SUPPORT` define and a reference to the `UniTask.DOTween` assembly. UI tweens that run during pause use `SetUpdate(true)`.
- Durations and eases come from configs or named constants and follow one motion language. No tweens created from per-frame code.

## Serialization and saving

Formats and the save pipeline: [references/serialization.md](references/serialization.md).

- **Interfaces in the Inspector:** `SerializedInterface<T>` (library) for references to MonoBehaviours and ScriptableObjects that implement `T`; `[SerializeReference]` for plain C# implementations, such as strategies inside configs.
- Persistence sits behind interfaces (`ISaveService<T>`, `ISaveStorage`) in its own domain (library Persistence module). Save data is plain DTOs, mapped to and from runtime state, with a schema version and forward migrations. Writes are atomic.
- Never `BinaryFormatter`. `PlayerPrefs` only for small device-local preferences, never progress.
- When renaming a serialized field, add `[FormerlySerializedAs("oldName")]`, or the assigned values are lost.

## Configs and content data

- **One config per service or feature**, as a ScriptableObject. The class lives in the domain's `Configs/` folder, its assets in `Assets/_Project/Configs/<Domain>/`. Configs are injected, never referenced from services directly.
- **Read-only at runtime.** Never write to a ScriptableObject at runtime: in the Editor the change is saved into the asset, in a build it's lost on restart.
- Validate with `[Range]`, `[Min]`, `[Tooltip]` and `OnValidate()`. Build custom inspectors or editor windows whenever they make authoring faster or safer.
- **Definitions hold data only.** A content ScriptableObject (scenario, item, ability, enemy type) never holds runtime state, subscriptions or logic: every user shares the same asset, the Editor keeps its state between play sessions, and Unity creates it outside DI. A factory creates a plain C# runtime object from it (`ScenarioDefinition` → `ScenarioRuntime`). Polymorphic parts use `[SerializeReference]` or `SerializedInterface<T>`.
- **Levels**, when they don't need to be separate scenes, are chosen per project:
  - a scene per level: large hand-built environments with their own lighting bake, NavMesh or occlusion data;
  - a prefab per level loaded through Addressables: hand-built levels that share one scene setup;
  - a ScriptableObject definition: levels described by data (grids, wave lists, parameters, generated levels);
  - a definition plus a prefab: data plus hand-built geometry, the definition holding an `AssetReference` to the prefab.
- **No direct references to level content** from a level list: a direct reference loads every level with the list. Use `AssetReference` and load and release one level at a time.
- **No `Resources/` folder** for the project's content: everything in it ships in the build and is indexed at startup. Use Addressables or serialized references. The exception is a settings asset that a third-party package loads from `Resources/` by design, such as DOTween's.

## Packages

- Third-party packages come from OpenUPM when published there, otherwise from a git URL pinned to a release tag (`...git?path=...#1.2.3`). Never an unpinned git URL: it changes under the project without warning.
- Add packages through the Package Manager Client API (`unity:unity-package-management`). Remove packages the project doesn't use: they cost compile time and build size.

## Per-frame code and memory

Budgets, rendering and profiling are in the [performance guide](../performance/SKILL.md).

- **No allocations in per-frame code:** no LINQ, no capturing lambdas, no boxing, no string building (use TMP `SetText(format, value)`), no new collections (reuse, or rent from `ListPool<T>` / `ArrayPool<T>`).
- **No `Update`, `FixedUpdate` or `LateUpdate` in our MonoBehaviours.** Per-frame work runs in `ITickable` systems that iterate over their objects. Non-critical work runs every N frames; heavy work is spread across frames.
- **No component lookups at runtime:** no `GetComponent`, `Find*` or `FindObjectsByType` in runtime paths. Serialize, inject, or cache during initialization (`TryGetComponent` when a lookup there is unavoidable). Use `CompareTag`. Cache `Animator.StringToHash` and `Shader.PropertyToID` in `static readonly` fields.
- Physics queries use non-allocating overloads with preallocated buffers and a layer mask.
- **No reflection in runtime code.** Editor code finds types with `TypeCache`.
- **Pooling.** Objects created and destroyed repeatedly (projectiles, effects, enemies, list items, audio sources) are pooled with the library's Pooling module: one pool per prefab shared by all users, sized to the peak alive count, prewarmed during loading, never at first use. Pooled objects implement `IPoolable` and reset all state on return.
- **Off-screen objects.** Built-in culling first (Animator and particle culling modes, renderer visibility). For custom behavior, a `CullingGroup` drives `IPausable` components.
- **Data layout.** Order struct fields largest to smallest. Hot data in contiguous arrays, struct-of-arrays in tight loops, large structs passed with `in`. Structs used as keys or compared implement `IEquatable<T>`.
- **Burst and jobs** for heavy parallel work over thousands of elements: `Unity.Mathematics`, no managed objects, native containers disposed deterministically. Remove only unpredictable branches in hot loops (`math.select`), check the Burst Inspector and measure. Entities (ECS) is an architecture decision made with the user.
- **Logging** goes through the library's `Log`: `Log.Debug` compiles out of release builds together with its message; warnings, errors and exceptions are always logged.

## Resource lifetimes

Every resource has one owner that releases it on every path, including cancellation, despawn, scene unload and quit. Read [references/resource-lifetimes.md](references/resource-lifetimes.md) before writing or reviewing code that subscribes, loads, allocates, pools or creates objects at runtime. In short:

- Subscriptions (MessagePipe, Providers, C# and static events, Input System callbacks) are disposed or removed by their owner.
- VContainer disposes only the `Singleton` and `Scoped` instances it created; `RegisterInstance` objects, `Transient` objects and GameObjects are released by their creator.
- Every Addressables load has exactly one release, owned by the loading service.
- Unity objects created at runtime (meshes, materials, textures, render textures, sprites) are destroyed by their owner. `renderer.material` and `meshFilter.mesh` create copies the caller owns: use `sharedMaterial` and `sharedMesh`.
- Native containers, GPU buffers, `CullingGroup`s, `UnityWebRequest`s and streams are disposed deterministically. No finalizers.
- `Dispose` is idempotent and never throws.

## Tests

- Logic is tested in Edit Mode through its interfaces, with hand-written fakes. Play Mode tests only for what needs the running engine: scenes, physics, frames, rendering.
- A test is named for the behavior it checks (`CancelledLoad_ReleasesItsHandle`) and checks one behavior.
- Deterministic: time and randomness are injected (a seeded `System.Random`), and nothing waits on real time.
- Every test cleans up what it creates: GameObjects, assets, scopes, files, static subscriptions.
- Hot paths have allocation tests (`Is.Not.AllocatingGCMemory()`). Disposable types have disposal tests: twice, after use, with work in flight.
- A bug fix starts with a test that reproduces the bug.
- Async tests return `UniTask.ToCoroutine(async () => ...)` from a `[UnityTest]`.

## Code style

| Element | Style | Example |
|---|---|---|
| Types, methods, properties | PascalCase | `DamageService`, `ApplyDamage()` |
| Interfaces | `I` + PascalCase | `IDamageable` |
| Private fields, serialized ones included | `_camelCase` | `[SerializeField] private float _speed;` |
| Parameters, locals | camelCase | `damageAmount` |
| Constants, `static readonly` | PascalCase | `MaxHealth` |
| Async methods | `Async` suffix | `LoadLevelAsync()` |
| Booleans | `Is` / `Has` / `Can` | `IsAlive` |
| Events and handlers | Event: a verb, no `On`. Handler: `On` + event | `Completed`, `OnCompleted()` |
| Generic variants | Same name with a type parameter | `IExecutable<T>`, not `IExecutableGeneric<T>` |

- Access modifiers are always explicit, `private` on serialized fields included.
- Names are real English words, spelled correctly: a typo in a serialized field or public API lives as long as the project.
- **Comments are rare.** Names explain the code; a comment explains only why: a non-obvious decision, a workaround, a performance trick. No commented-out code.
- No magic numbers or strings: configs or named constants.
- Use Unity and package attributes freely (`[SerializeField]`, `[Header]`, `[Tooltip]`, `[Range]`, `[Min]`, `[RequireComponent]`, `[DisallowMultipleComponent]`). Write custom attributes and property drawers when they make the Inspector safer or faster.
- Extension methods: one static class per extended type (`TransformExtensions`). Generic ones live in `Core/Extensions/` (start from the library's Extensions module), project-specific ones in the domain that uses them.
- **Fail fast and loud.** No catch-all blocks that return `null`. Validate serialized references in `OnValidate()` and at startup, with a clear message and the context object.

## Before finishing

- The code compiles with no errors or warnings: check the C# language server diagnostics, then let Unity recompile and read its console.
- Changes visible at runtime were checked in Play Mode.
- Each rule above holds for the changed code: right domain and assembly, DI instead of statics, every resource released by its owner, cancellation passed down, no per-frame allocations.
- The APIs the code relies on were checked for the project's package versions, not recalled from memory.
