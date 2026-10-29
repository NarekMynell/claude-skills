# Resource lifetimes

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

Every resource has one owner, and the owner releases it on every path: success, failure, cancellation, despawn, scene unload and quit. Most Unity leaks are native memory or callbacks into dead objects, which the garbage collector never cleans up.

## Ownership

- The code that creates or acquires a resource owns it. Ownership moves only when an API says so: a factory's `Create` hands what it returns to the caller.
- Never dispose what you didn't create, such as an injected dependency.
- A type that owns a disposable, a subscription, a native buffer or a Unity object it created implements `IDisposable` and releases them there.
- **VContainer** disposes the `IDisposable` instances it created itself, with `Lifetime.Singleton` or `Lifetime.Scoped` (entry points included), newest first, when their scope's container is disposed: the scope is destroyed, `Dispose()`d or unloaded with its scene. It never disposes instances passed to `RegisterInstance`, anything `Transient`, or GameObjects, including those made by `IObjectResolver.Instantiate`: their creator releases them.

## Implementing IDisposable

- A `sealed` class with a plain `Dispose()`. Use the `Dispose(bool)` pattern only in a class designed for inheritance.
- Idempotent: a second call does nothing. It releases in reverse order of acquisition and never throws: VContainer disposes a scope's objects one after another without catching, so one throwing `Dispose` skips the rest.
- After `Dispose`, a call that needs the released resources throws `ObjectDisposedException`; anything else is a documented no-op.
- No finalizers: they run on the garbage collector's thread, where Unity APIs can't be called, and they hide leaks instead of fixing them.
- A constructor that acquires several resources and fails partway releases what it already acquired.

## Where to release

- **Plain C# services:** in `Dispose()`, which the container calls.
- **MonoBehaviours:** what `OnEnable()` acquires, `OnDisable()` releases; what `Awake()` or `Start()` acquires, `OnDestroy()` releases.
- **`Construct` only stores dependencies.** VContainer injects before `Awake`, also into objects that never become active (an inactive prefab, an instance created under an inactive parent), and `OnDestroy` runs only on objects that were active at some point. A subscription made in `Construct` can outlive its object.
- **Pooled objects are deactivated, never destroyed,** so `OnDestroy`, `destroyCancellationToken` and `SetLink(gameObject)` don't fire on despawn. What a spawn starts, `OnDespawned` ends: the spawn's own `CancellationTokenSource`, its tweens, its subscriptions, and every field it changed.
- **Async work:** a service owns a `CancellationTokenSource`, which `Dispose()` cancels and then disposes. MonoBehaviours pass `destroyCancellationToken`, read while the object is alive (Unity's documentation: cache it before the object is destroyed). An `IAsyncStartable` uses the token VContainer passes to `StartAsync`, which is cancelled when its scope is disposed.
- **Scene objects using app-wide services** (root scope) release their subscriptions themselves: the root outlives every scene.

## Subscriptions

- **MessagePipe.** `Subscribe` returns an `IDisposable` that must be kept: an ignored return value leaks. Collect subscriptions with `DisposableBag.CreateBuilder()` and `Build()`, and dispose the bag with the owner; a MonoBehaviour can bind one with UniTask's `.AddTo(destroyCancellationToken)`. Disposing a broker's scope drops its subscriptions, but brokers live in the root scope, so that happens only at quit: scene code disposes its own.
- **Messages carry values, not ownership.** No `IDisposable`, pooled object or native container in a message, and no `UnityEngine.Object` that can be destroyed or returned to a pool before an async handler runs. A handler that must reference an object checks it with `IsAlive()`.
- **A throwing MessagePipe handler** stops the handlers after it, and the exception reaches the publisher. Each handler deals with its own expected failures.
- **Providers:** `Subscribe` returns an `IDisposable`; dispose it the same way.
- **C# events:** `-=` the same delegate that was added. A lambda can't be removed, so subscribe a method or a stored delegate.
- **Static events** (`SceneManager.sceneLoaded`, `Application.lowMemory`, `Application.focusChanged`, `InputSystem.onDeviceChange`) keep every subscriber alive and call into it after it is destroyed. Always unsubscribe.
- **UnityEvents** added in code with `AddListener` are removed with `RemoveListener` when the listener dies before the event's owner.
- **Input System:** `action.performed += OnFire` is paired with `-=`. Actions are enabled and disabled by their owner. A generated input actions class is `IDisposable` (it destroys the asset copy it created): dispose it with its owner.

## Async and cancellation

- **Dispose every `CancellationTokenSource`** after cancelling it or when it is no longer needed. Linked sources (`CreateLinkedTokenSource`) register on their parent tokens and leak until disposed. A restartable operation cancels and disposes the previous source before creating the next. Dispose a `CancellationTokenRegistration` once its callback is no longer needed.
- **Timeouts** use UniTask's `CancelAfterSlim`, which runs on the player loop, instead of `CancelAfter`, which uses a thread timer; dispose the `IDisposable` it returns.
- **Tokens by lifetime:** `destroyCancellationToken` for a MonoBehaviour's work, the service's own source for a service, `Application.exitCancellationToken` for work that lasts until the app quits.
- **Release in `finally`.** A resource acquired in an async method is released in `finally` or by `using`, so cancellation and exceptions release it too, including when cancellation arrives after the acquisition but before the hand-over.
- **`OperationCanceledException` means "stopped on request".** Let it propagate. Catch it only at the top of the chain to stop quietly; never log it as an error, never swallow it in the middle. UniTask's `Forget()` ignores it by default, but VContainer passes everything an `IAsyncStartable` throws, cancellation included, to its entry point exception handler (`Debug.LogException` unless `RegisterEntryPointExceptionHandler` sets another): an async entry point ends its own shutdown quietly.
- **A `UniTask` is awaited once.** Awaiting it again is undefined; use `.Preserve()` to share one.

## Addressables

- **Mirror every load with one release.** `LoadAssetAsync` → `Addressables.Release` with the handle or the loaded asset, never with an instance made from it. `AssetReference.LoadAssetAsync` → `ReleaseAsset()`. `Addressables.LoadSceneAsync` → `Addressables.UnloadSceneAsync`. The library's ContentLoading module owns handles and counts loads.
- **No `Addressables.InstantiateAsync`:** instances need injection. Load the prefab through the content loader, instantiate it through the resolver with a parent or a factory, destroy the instances, then release the prefab.
- **Released isn't unloaded.** An AssetBundle unloads only when none of its assets is in use, so group content that loads and unloads together. Releasing and immediately reloading the same content (churn) reloads its bundles.

## Unity objects created at runtime

- **Not garbage collected.** Meshes, materials, textures, render textures, sprites, audio clips and ScriptableObjects created at runtime (`new`, `Instantiate`, `Sprite.Create`, `AudioClip.Create`, `ScriptableObject.CreateInstance`, textures loaded from files or the web) are destroyed with `Object.Destroy` by their owner. `Resources.UnloadUnusedAssets` frees only what nothing references and stalls the frame; Unity runs it by itself on a single-mode scene load. Never rely on it.
- **Hidden copies.** `Renderer.material`, `Renderer.materials` and `MeshFilter.mesh` create a copy on first access, which the caller must destroy (Unity's documentation says so), and each copy is one more asset in memory. Read and assign `sharedMaterial` and `sharedMesh`; for per-object looks, see the [performance guide](../../performance/SKILL.md#repeated-objects).
- **Render textures.** `RenderTexture.Release()` frees the GPU memory but not the object: destroy it too. Short-lived ones use `RenderTexture.GetTemporary` / `ReleaseTemporary` in pairs.
- **URP renderer features** release what they create in a `Dispose(bool disposing)` override: materials from `CoreUtils.CreateEngineMaterial` with `CoreUtils.Destroy`, and imported `RTHandle`s. Textures created inside the render graph are managed by the graph.
- **GameObjects** live until destroyed. Pools own their instances. A scene unload destroys its own objects, not `DontDestroyOnLoad` ones, and `IObjectResolver.Instantiate` with the root scope's resolver and no parent creates `DontDestroyOnLoad` objects.

## Native memory and I/O

- **Native containers** (`NativeArray`, `NativeList` and the rest) get the allocator their lifetime needs: `Temp` within one frame, `TempJob` disposed within four frames, `Persistent` owned by a service that disposes it in `Dispose()`. A container used by a job is disposed after the job completes, or with `Dispose(jobHandle)`.
- **Engine handles:** `ComputeBuffer`, `GraphicsBuffer`, `CommandBuffer` and `CullingGroup` are released or disposed by their owner.
- **`UnityWebRequest`** is disposed after every request, successful or not: `using var request = UnityWebRequest.Get(url);`.
- **Streams and files:** `using` declarations, never a manual `Close` that an exception can skip.

## Tweens

- Every tween is tied to its owner with `SetLink(gameObject)`, or killed in `OnDestroy()` / `Dispose()`. A pooled object's tweens use `SetLink(gameObject, LinkBehaviour.KillOnDisable)` or are killed in `OnDespawned`. A tween inside a Sequence is controlled through the Sequence.
- A tween built with `SetAutoKill(false)` lives until it is killed: its owner kills it.
- **Awaiting:** `await tween.ToUniTask(TweenCancelBehaviour.KillAndCancelAwait, ct)`. With the default `TweenCancelBehaviour.Kill`, cancelling kills the tween but completes the await normally, so the code after it runs on an owner that may be gone. `ToUniTask` completes when the tween is killed, so a `SetAutoKill(false)` tween is awaited with `AwaitForComplete(TweenCancelBehaviour.CancelAwait, ct)` instead. Both need the `UNITASK_DOTWEEN_SUPPORT` define and a reference to the `UniTask.DOTween` assembly.

## Static state and Enter Play Mode

With domain reload disabled (Unity 6.6's default, and Unity's recommendation), static fields and static event subscriptions survive from one Play Mode run to the next. The code standards allow no mutable static state; where a static is unavoidable (the global resolver, a callback a third-party API requires), reset it on entering Play Mode. `[RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]` works in every Unity 6 version, `[InitializeOnEnterPlayMode]` in Editor code. Newer versions add lifecycle attributes for this (Unity 6.5: `[OnEnteringPlayMode]`, `[AutoStaticsCleanup]`): check the documentation of the project's version before using them.

## Finding leaks

Check during development, and before reporting work on loading, scenes or pooling as done:

- **Memory Profiler:** take a snapshot, load a level, leave it, take another, and compare. Nothing from the level remains: no meshes, materials, textures or GameObjects.
- **MessagePipe Diagnostics** window (**Window > MessagePipe Diagnostics**) for subscriptions that were never disposed; it needs the setup in the [DI reference](dependency-injection.md#messagepipe-registration). A Play Mode test can compare `MessagePipeDiagnosticsInfo.SubscribeCount` before a scene loads and after it unloads.
- **UniTask Tracker** window (**Window > UniTask Tracker**) for tasks that never complete.
- **Addressables Profiler module** for loaded content and reference counts.
- **Leak Detection Level** (**Preferences > Jobs**) set to **Enabled With Stack Trace** while hunting a native leak.
- **Tests** for every disposable type: dispose twice, use after dispose, dispose with operations in flight.
