# Library changes

This list can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

What each unity-dev release changed in the code library, so a project's copy can catch up, as [updating a copy](SKILL.md#updating-a-projects-copy) describes. **Fix** marks a defect that every copy of the module has: port it. **Change** alters an API or a behavior the project may rely on. **Added** is new code or tests.

## 0.6.0

Found by an independent review that proved each defect with a failing test; every fix comes with that test.

- **ContentLoading.** Fix: a cancelled load whose handle completed later could end another, unrelated load, which then failed and released its handle. UniTask 2.5.11's `ToUniTask` returns the cancelled awaiter to its pool while it's still subscribed to the old handle. `AddressablesContentLoader` now polls `IsDone` once per frame on the main thread, and the Core assembly no longer references `UniTask.Addressables`. A load still running at `Dispose` that then fails ends with `ObjectDisposedException`, as documented.
- **Persistence.** Fix: a save whose header was damaged, such as a zero-filled file after a power loss, was returned as legacy data instead of falling back to the intact backup. A headerless file now counts as legacy only when it holds JSON.
- **Persistence.** Change: when the save and its backup are both damaged, `LoadAsync` throws `InvalidDataException` instead of returning null, which callers answered with a new game that overwrote the save.
- **Persistence.** Fix: data nested deeper than 64 levels saved but couldn't load (Json.NET's reader limit), and data that isn't a JSON object, such as a list, couldn't load at all. Both load now; migrations still need an object.
- **Persistence.** Fix: a cancellation token was checked when an operation was queued, not when it started. Keys that are Windows device names (`con`, `nul`, `com1`…) are refused on every platform, since Windows can't create those files.
- **Scenes.** Fix: a second load was accepted while the first one's transition was still hiding, so show and hide ran at once. It now throws until the first load has returned.
- **Culling.** Fix: a target whose `Pause` or `Resume` threw aborted `Dispose` (the `CullingGroup` leaked and other targets stayed paused) and dropped the rest of a culling pass's events. Those exceptions are now logged; Culling depends on Logging.
- **Pooling.** Fix: a reused instance kept the local pose its last use left it in; it now starts from the pose it was created with. `Prewarm` failing partway left its instances outside the pool; a failed `Register` leaked a pool subscribed to `SceneManager.sceneUnloaded`. An `OnSpawned` that despawned its instance still let later components receive `OnSpawned`; a throwing `OnDespawned` lost the instance. Change: `Prewarm` above `maxSize` throws instead of destroying the extras.
- **Bootstrap.** Fix: after a shutdown, the flow still started the next step when the running one ignored the token, and could report `Completed`.
- **Algorithms.** Fix: `SpatialHash.Query` with a huge or infinite radius overflowed its cell range and found nothing. It scans the items then; a NaN radius throws. `GridPathfinder` no longer grows its queue when a longer search follows a short one on the same grid.
- **Serialization.** Fix: `SerializableDictionary` accepted an empty string key, which Unity stores for an unset string; it now counts as invalid.
- **DI.** Change: a `ComponentFactory<T>` given a parent throws once that parent is destroyed, instead of creating instances in the active scene.
- **Persistence.** Added: `Tests/PlayMode/SaveRoundTripTests`, the public API end to end on the platform's real file storage. It passes in macOS and WebGL (IL2CPP) players.

## 0.5.0

- **Persistence.** Fix: a power loss shortly after a save could leave it empty or partial: the data wasn't flushed to disk before the new file replaced the old save, and the backup was deleted at once. `FileSaveStorage` now flushes the temporary file to disk before the swap, keeps the previous save as a `.bak`, and reads the newest intact copy: each file starts with its length and a CRC-32, and a damaged save is restored from its backup. Files without the header, written by older versions, are still read.
- **Persistence.** Fix: each operation returned to the main thread before the next could start, so while the app was paused in the background, with no player loop, a queued save waited until the app resumed or was killed. Operations now run in order on the thread pool without the main thread, and `Dispose` gives pending writes 2 s on quit.
- **Persistence.** Change: `ISaveStorage` gained `bool Flush(TimeSpan timeout)`; custom storages implement it. `FileSaveStorage` and `JsonSaveService` are `internal`: register them with `RegisterFileSaveStorage()` and `RegisterJsonSave<T>(schema)`. Operations after `Dispose` throw `ObjectDisposedException`. The assembly no longer references Core.
- **Persistence.** Fix: `JsonSaveService` used `JsonSerializer.CreateDefault`, so a plugin setting the global `JsonConvert.DefaultSettings` changed the save format. It uses `JsonSerializer.Create()` and streams the JSON.
- **Scenes.** Fix: `SceneLoader` held the scene before activation while the transition showed, which stalls every later `AsyncOperation`: a transition that awaited one never finished (reproduced in a macOS player build). The scene now activates as soon as it has loaded.
- **Scenes.** Change: cancellation stops a load only before it starts; a started load finishes and returns normally. A second load while one runs throws `InvalidOperationException`. The path is validated before the transition shows, and the transition is always hidden.
- **Pooling.** Fix: instances destroyed with their scene broke the pool on their next spawn. `ComponentPool` now forgets destroyed instances, and despawning one does nothing. Change: the container is required; `Dispose` is idempotent; after it, `Spawn` throws and despawned items are destroyed.
- **Pooling.** Change: `PrefabPoolRegistry` requires a container and throws `ObjectDisposedException` after `Dispose`. Register it as a Singleton.
- **DI.** Fix: `ComponentFactory<T>` without a parent created instances in `DontDestroyOnLoad` when its resolver was the root scope's, so they outlived every scene. They now join the active scene.
- **Culling.** Change: `VisibilityPauser.Dispose` is idempotent; `Register` and `UpdatePosition` throw `ObjectDisposedException` after it.
- **Bootstrap.** Fix: quitting during startup logged the cancellation as an error. `BootstrapFlow` now ends quietly when its own scope shuts down.
- **Bootstrap (Editor).** Fix: Play from Bootstrap could open a scene left by an earlier start, and picked the first scene even when it was disabled. It now clears the stale scene and uses the first enabled scene.
- **Serialization (Editor).** Fix: `SubclassSelector` offered types from Play Mode test assemblies, which builds leave out. It lists player assemblies without test assemblies.
- **Audio.** Change: `AudioService` is `internal`; register it with `RegisterAudio(settings)`.

## 0.1.0 to 0.4.0

The library's first version; its code didn't change across these releases.
