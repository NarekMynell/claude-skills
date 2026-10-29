# Pooling

Prewarmed component pools built on `UnityEngine.Pool`, one shared pool per prefab.

- **Destination:** `Core/Pooling/`
- **Depends on:** DI, Extensions; VContainer.

```csharp
// Installer of the scope whose content the pools serve. The container is an active, empty GameObject in the
// same scope's prefab or scene: the registry's pools keep their inactive instances under it.
builder.Register(resolver => new PrefabPoolRegistry(resolver, _poolContainer), Lifetime.Singleton);

// During loading
var bullets = _pools.Register(_bulletPrefab, prewarmCount: 64);

// Gameplay
var bullet = _pools.Get(_bulletPrefab).Spawn(muzzle.position, muzzle.rotation);
_pools.Get(_bulletPrefab).Despawn(bullet);
```

- **Lifetime.** `Singleton`, so child scopes share the registry's pools; `Scoped` would give each child scope an empty registry. Register the registry in the scope whose content it pools: a scene's effects in the scene scope, app-wide pools (UI, audio voices) in the root scope with a container under `DontDestroyOnLoad`.
- `PrefabPoolRegistry` creates instances through the resolver, so they receive injection. Asking for an unregistered prefab throws: prewarming can't be forgotten silently.
- `Spawn` places the instance before activating it, then calls `IPoolable.OnSpawned` on every `IPoolable` in its hierarchy. A reused instance starts from the local position, rotation and scale it was created with, like a new one; `Spawn(position, rotation)` then sets its world position and rotation. Without a parent, the instance joins the active scene, like `Object.Instantiate`, even when the pool's container is `DontDestroyOnLoad`.
- An `OnSpawned` that despawns its own instance ends the spawn: the components after it get no `OnSpawned`. A throwing `OnDespawned` still returns the instance to the pool, then the exception reaches the caller.
- `Despawn` calls `OnDespawned`, deactivates the instance and returns it to the container. Despawning a foreign object, or one already in the pool, throws.
- **Destroyed instances.** An instance destroyed outside the pool, such as one that joined a scene that has since unloaded, is forgotten: despawning it does nothing, and it is never spawned again.
- `Prewarm(n)` makes at least `n` instances wait inactive, without spawn callbacks; `n` above the pool's `maxSize` throws. Their `Awake` runs then, during loading. If creating one fails, the ones already made wait in the pool, and a `Register` whose prewarm fails disposes its new pool before rethrowing.
- **Dispose** destroys the inactive instances; active ones stay with their users, and despawning one afterwards destroys it. `Spawn`, `Prewarm`, `Register` and `Get` throw `ObjectDisposedException` after `Dispose`.
- **Pooled objects are deactivated, never destroyed,** so `OnDestroy`, `destroyCancellationToken` and `SetLink(gameObject)` don't fire on despawn. Whatever a spawn starts, `OnDespawned` ends: cancel and dispose that spawn's `CancellationTokenSource`, kill its tweens (or link them with `LinkBehaviour.KillOnDisable`), dispose its subscriptions, and reset every field.
