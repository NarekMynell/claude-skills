# Dependency injection (VContainer)

## Scope setup

1. **Root scope.** A prefab with a `ModularLifetimeScope` (DI module) and the app-wide installers. Create the settings asset with **Assets > Create > VContainer > VContainer Settings** and assign the prefab to **Root Lifetime Scope**. The asset adds itself to Player Settings > Preloaded Assets. VContainer then instantiates the root with the first scene, marks it `DontDestroyOnLoad`, and makes it the parent of every scope that has no explicit parent.
2. **Scene scope.** One `ModularLifetimeScope` per scene, with that scene's installers listed in order.
3. **Child scopes** for a prefab or a temporary context (a level, a popup): `scope.CreateChildFromPrefab(prefab)` or `scope.CreateChild(installer)`. Dispose them with the context.

## Domain installer

```csharp
internal sealed class CombatInstaller : ScopeInstaller
{
    [SerializeField] private CombatConfig _config;
    [SerializeField] private CombatHud _hud;

    public override void Install(IContainerBuilder builder)
    {
        builder.RegisterInstance(_config);
        builder.Register<IDamageService, DamageService>(Lifetime.Singleton);
        builder.RegisterEntryPoint<ProjectileSystem>();
        builder.RegisterComponent(_hud);
    }
}
```

- An installer registers only its own domain.
- Scene and config references are serialized on the installer, never looked up.
- Lifetimes: `Singleton` for services of the scope, `Scoped` only when child scopes need their own instance, `Transient` only for stateless or factory-made objects.

## Entry points instead of MonoBehaviour lifecycle

```csharp
internal sealed class ProjectileSystem : ITickable, IDisposable
{
    private readonly IProjectilePool _pool;

    public ProjectileSystem(IProjectilePool pool) => _pool = pool;

    public void Tick() { /* iterate active projectiles; no allocations */ }

    public void Dispose() => _pool.ReleaseAll();
}
```

## Typed factory

```csharp
public interface IEnemyFactory
{
    IEnemy Create(EnemyDefinition definition, Vector3 position);
}

internal sealed class EnemyFactory : IEnemyFactory
{
    private readonly IObjectResolver _resolver;

    public EnemyFactory(IObjectResolver resolver) => _resolver = resolver;

    public IEnemy Create(EnemyDefinition definition, Vector3 position)
    {
        var enemy = _resolver.Instantiate(definition.Prefab, position, Quaternion.identity);
        enemy.Initialize(definition);
        return enemy;
    }
}
```

`IObjectResolver.Instantiate` injects the new object's hierarchy. A plain `Object.Instantiate` would leave its `[Inject]` members empty.

## MessagePipe registration

In the root scope's installer:

```csharp
var options = builder.RegisterMessagePipe();
builder.RegisterMessageBroker<LevelCompleted>(options);
```

Each message type is registered once, in the scope whose lifetime matches it. `GlobalMessagePipe.SetProvider(resolver.AsServiceProvider())` is set only when code that DI can't reach must publish, under the global-resolver rule.

## Source generator

VContainer injects through reflection unless its source generator is installed:

1. Download `VContainer.SourceGenerator.dll` (the file VContainer's documentation names, not the `Roslyn3` variant) from the GitHub release whose tag equals the installed VContainer version: `https://github.com/hadashiA/VContainer/releases/download/<version>/VContainer.SourceGenerator.dll`.
2. Place it under `Assets/Plugins/VContainer/`.
3. In its import settings, disable **Any Platform**, **Editor** and **Standalone**, and give it the asset label `RoslynAnalyzer`.

It generates injectors for types in assemblies that reference `VContainer` and are registered or carry `[Inject]`. Not covered: nested classes, structs, and types less accessible than `internal`. Generated types are `[Preserve]`d against IL2CPP stripping.

## Global resolver

Last resort, for code that DI can't reach. If used:

- exactly one static access point, in Core (the library's DI module provides it);
- it is set when its scope is built and cleared when that scope is disposed, so it never points to a dead container;
- every call site has a comment explaining why DI couldn't be used.

## Diagnostics

Enable **VContainer Diagnostics** in `VContainerSettings` during development to see registrations, resolutions and their call sites (Window > VContainer Diagnostics). Disable it in release builds.
