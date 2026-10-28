# Pooling

Prewarmed component pools built on `UnityEngine.Pool`, one shared pool per prefab.

- **Destination:** `Core/Pooling/`
- **Depends on:** DI, Extensions; VContainer.

```csharp
// Installer: the registry owns the container its inactive instances wait under.
builder.Register(resolver => new PrefabPoolRegistry(resolver, _poolContainer), Lifetime.Scoped);

// During loading
var bullets = _pools.Register(_bulletPrefab, prewarmCount: 64);

// Gameplay
var bullet = _pools.Get(_bulletPrefab).Spawn(muzzle.position, muzzle.rotation);
_pools.Get(_bulletPrefab).Despawn(bullet);
```

- `PrefabPoolRegistry` creates instances through the resolver, so they receive injection. Asking for an unregistered prefab throws: prewarming can't be forgotten silently.
- `Spawn` places the instance before activating it, then calls `IPoolable.OnSpawned` on every `IPoolable` in its hierarchy. Without a parent, the instance joins the active scene, like `Object.Instantiate`, even when the pool's container is `DontDestroyOnLoad`.
- `Despawn` calls `OnDespawned`, deactivates the instance and returns it to the container. Despawning a foreign object, or one already in the pool, throws.
- `Prewarm(n)` makes at least `n` instances wait inactive, without spawn callbacks.
- `Dispose` destroys the inactive instances; active ones stay with their users.
