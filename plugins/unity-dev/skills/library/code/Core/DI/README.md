# DI

VContainer composition building blocks.

- **Destination:** `Core/DI/`
- **Depends on:** VContainer.

| Type | Use |
|---|---|
| `ModularLifetimeScope` | The scope of a scene or of the root prefab. Lists its `ScopeInstaller`s in the Inspector and runs them in that order. An empty slot throws with the scope's name. |
| `ScopeInstaller` | Base of each domain's installer: `Install(IContainerBuilder)`, with the domain's scene and config references as serialized fields |
| `IFactory<T>`, `ComponentFactory<T>` | Typed creation through `IObjectResolver.Instantiate`, so new hierarchies receive injection |
| `GlobalResolver` | Last resort for code DI can't reach. Enable **Expose As Global Resolver** on one scope (usually the root); it's cleared when that scope's container is disposed (destroyed, `Dispose()`d or unloaded with its scene) and on entering Play Mode |

```csharp
internal sealed class CombatInstaller : ScopeInstaller
{
    [SerializeField] private CombatConfig _config;

    public override void Install(IContainerBuilder builder)
    {
        builder.RegisterInstance(_config);
        builder.Register<IDamageService, DamageService>(Lifetime.Singleton);
    }
}
```

Setup: the root scope is a prefab assigned in `VContainerSettings`; see the code standards' DI reference.
