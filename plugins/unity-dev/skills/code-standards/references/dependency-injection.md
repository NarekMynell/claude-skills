# Dependency injection (VContainer)

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

## Scope setup

1. **Root scope.** A prefab with a `ModularLifetimeScope` (DI module) and the app-wide installers, assigned to **Root Lifetime Scope** in a `VContainerSettings` asset. VContainer finds the settings only in **Player Settings > Preloaded Assets**, in the Editor too. **Assets > Create > VContainer > VContainer Settings** adds the new asset there, but it opens a save dialog; an asset created by script is added with `PlayerSettings.SetPreloadedAssets`. Check that it's listed. VContainer then instantiates the root with the first scene, marks it `DontDestroyOnLoad`, and makes it the parent of every scope that has no explicit parent.
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
- Scene and config references are serialized on the installer, never looked up: no `RegisterComponentInHierarchy`, which searches the scene. Scene objects that only receive injection go in the scope's **Auto Inject Game Objects** list.
- Lifetimes: `Singleton` for services of the scope, `Scoped` only when child scopes need their own instance, `Transient` only for stateless or factory-made objects.
- **Disposal:** the container disposes the `IDisposable` instances it created as `Singleton` or `Scoped`, newest first, when the scope is disposed. It never disposes `RegisterInstance` or `Transient` objects, or GameObjects. Details: [resource lifetimes](resource-lifetimes.md).

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

- `IAsyncStartable.StartAsync(CancellationToken)` gets a token that VContainer cancels when the scope is disposed.
- VContainer passes exceptions from entry points, cancellations from `StartAsync` included, to its entry point exception handler: `Debug.LogException` unless `builder.RegisterEntryPointExceptionHandler(...)` sets another. An async entry point ends its own shutdown quietly instead of rethrowing the cancellation.

## Typed factory

```csharp
public interface IEnemyFactory
{
    IEnemy Create(EnemyDefinition definition, Vector3 position);
}

internal sealed class EnemyFactory : IEnemyFactory
{
    private readonly IObjectResolver _resolver;
    private readonly Transform _enemyRoot;

    public EnemyFactory(IObjectResolver resolver, Transform enemyRoot)
    {
        _resolver = resolver;
        _enemyRoot = enemyRoot;
    }

    public IEnemy Create(EnemyDefinition definition, Vector3 position)
    {
        var enemy = _resolver.Instantiate(definition.Prefab, position, Quaternion.identity, _enemyRoot);
        enemy.Initialize(definition);
        return enemy;
    }
}
```

- The installer passes the parent: `builder.Register<IEnemyFactory>(resolver => new EnemyFactory(resolver, _enemyRoot), Lifetime.Singleton);`.
- `IObjectResolver.Instantiate` injects the new object's hierarchy, before its `Awake`. A plain `Object.Instantiate` would leave its `[Inject]` members empty.
- **Placement.** Without a parent, `IObjectResolver.Instantiate` puts the object in the scope's scene, and with the root scope's resolver it marks it `DontDestroyOnLoad`, so it outlives every scene. Register the factory in the scope that owns what it creates, or give every instance a parent, as above. The library's `ComponentFactory<T>` puts parentless instances in the active scene.
- The caller owns what a factory returns and destroys it; the container never does.

## MessagePipe registration

MessagePipe is registered once, in the root scope's installer:

```csharp
var options = builder.RegisterMessagePipe();
// The MessagePipe Diagnostics window and GlobalMessagePipe need the global provider.
builder.RegisterBuildCallback(c => GlobalMessagePipe.SetProvider(c.AsServiceProvider()));
```

- **No registration per message type.** With Unity 2022.1+ and VContainer 1.14+, MessagePipe registers `IPublisher<T>` and `ISubscriber<T>` (and their async and buffered variants) as open generics: its asmdef defines `MESSAGEPIPE_OPENGENERICS_SUPPORT` when VContainer is installed. Request handlers and keyed brokers are registered explicitly, in the same root installer: `RegisterRequestHandler<TRequest, TResponse, THandler>(options)`, `RegisterAsyncRequestHandler<…>(options)`, `RegisterMessageBroker<TKey, T>(options)`.
- **One broker per message type, in the root.** Never call `RegisterMessagePipe` or `RegisterMessageBroker<T>` in a child scope: a second broker for the same type splits the channel, and publishers and subscribers in different scopes stop seeing each other. Scene code disposes its own subscriptions.
- `GlobalMessagePipe` has no reset; the root scope sets it again each time it is built, including every Play Mode run. Code still uses it only under the global-resolver rule.

## Source generator

VContainer injects through reflection unless its source generator is installed:

1. Download `VContainer.SourceGenerator.dll` (the file VContainer's documentation names, not the `Roslyn3` variant) from the GitHub release whose tag equals the installed VContainer version: `https://github.com/hadashiA/VContainer/releases/download/<version>/VContainer.SourceGenerator.dll`. Some releases ship no files (1.18.0 is one): then take the newest earlier release that has the DLL, and record that version in `docs/architecture.md`.
2. Place it under `Assets/Plugins/VContainer/`.
3. In its import settings, disable **Any Platform**, **Editor** and **Standalone**, and give it the asset label `RoslynAnalyzer`.

It generates injectors for types in assemblies that reference `VContainer` and are registered or carry `[Inject]`. Not covered: nested classes, structs, and types less accessible than `internal`. Generated types are `[Preserve]`d against IL2CPP stripping.

## Global resolver

Last resort, for code that DI can't reach. If used:

- exactly one static access point, in Core (the library's DI module provides it);
- it is set when its scope is built and cleared when that scope is disposed, so it never points to a dead container;
- every call site has a comment explaining why DI couldn't be used.

## Diagnostics

Enable **VContainer Diagnostics** in `VContainerSettings` during development to see registrations, resolutions and their call sites (**Window > VContainer Diagnostics**). It isn't Editor-only: player builds with it on capture a stack trace per registration. Keep it off in release builds, enforced by a build preprocessor that fails a release build when it's on.
