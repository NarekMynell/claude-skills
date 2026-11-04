# Capabilities and interfaces

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

The architecture is a must; which of the shapes below fits a given feature is your decision. A decision to leave the architecture isn't yours: it is the user's.

## The capability map

Every project keeps this table in `docs/architecture.md`, written before the code it describes and kept current with it:

| Capability | Interface | Implemented by | Used by |
|---|---|---|---|
| Moves | `IMovable` | `Drone`, `Tank`, `Visitor` | `PathFollower`, `Steering` |
| Shoots | `IShooter` | `Drone`, `Turret` | `FireControl` |
| Can be hit | `IDamageable` | `Drone`, `Tank`, `Turret` | `Projectile`, `Explosion` |
| Fires everything at once | `IFireControl` | `FireControl` | whatever chooses the target |

A row with one implementer is fine: the interface is what lets its users stay ignorant of it, and lets tests fake it. `ProjectArchitectureTests` compares the Interface column with the code, both ways.

## Objects that do several things

```csharp
public interface IMovable
{
    Vector3 Position { get; }
    void MoveTo(Vector3 destination);
}

public interface IFlying
{
    float Altitude { get; set; }
}

public interface IShooter
{
    void ShootAt(Vector3 target);
}

public interface IDamageable
{
    void TakeDamage(int amount);
}

internal sealed class Drone : MonoBehaviour, IMovable, IFlying, IShooter, IDamageable
{
    private IMover _mover;
    private IGun _gun;
    private IHealth _health;

    [Inject]
    public void Construct(IMover mover, IGun gun, IHealth health)
    {
        _mover = mover;
        _gun = gun;
        _health = health;
    }

    public Vector3 Position => transform.position;
    public float Altitude { get; set; }

    public void MoveTo(Vector3 destination) => _mover.MoveTo(transform, destination);
    public void ShootAt(Vector3 target) => _gun.Fire(transform.position, target);
    public void TakeDamage(int amount) => _health.Reduce(amount);
}

internal sealed class Turret : MonoBehaviour, IShooter, IDamageable
{
    private IGun _gun;
    private IHealth _health;

    [Inject]
    public void Construct(IGun gun, IHealth health)
    {
        _gun = gun;
        _health = health;
    }

    public void ShootAt(Vector3 target) => _gun.Fire(transform.position, target);
    public void TakeDamage(int amount) => _health.Reduce(amount);
}

public interface IFireControl
{
    void FireAll(Vector3 target);
}

internal sealed class FireControl : IFireControl
{
    private readonly IReadOnlyList<IShooter> _shooters;

    public FireControl(IReadOnlyList<IShooter> shooters) => _shooters = shooters;

    public void FireAll(Vector3 target)
    {
        foreach (var shooter in _shooters) shooter.ShootAt(target);
    }
}
```

`Drone` and `Turret` share a gun by composition, not through a `ShootingUnit` base class that would then have to decide whether towers can move. `FireControl` works with anything that shoots, including what doesn't exist yet.

The same capability can also live in a component of its own (`Gun : MonoBehaviour, IShooter`) on any object that needs it. Choose by what reads best in the Inspector and what shares state: a capability with its own state and references is usually its own component.

**Reaching a capability from the world.** A physics hit gives a `Collider`, not a capability. Where hits are rare, `TryGetComponent<IDamageable>` on the hit object is fine. Where they are frequent, a registry built at spawn (`Dictionary<Collider, IDamageable>`) answers without a lookup. Interface references to Unity objects follow the Unity null rule.

## When inheritance is right

| Case | Why |
|---|---|
| `MonoBehaviour`, `ScriptableObject`, the library's `ScopeInstaller` | The framework's shape, not a design choice |
| An abstract `Screen` with the open and close sequence that every screen shares exactly | True is-a, real shared behavior, one level, and the screens still implement their own interfaces |

Not right: a base class to reuse a helper method (make it a service or an extension), a base class for "things that can do X" (that is an interface), a second level (compose instead).

## A new kind without touching old code

A `switch` on a kind, repeated across the code, is where the next feature breaks everything. Each kind implements the interface, and data says which one a thing uses:

```csharp
public interface IAnimalBehavior
{
    AnimalAction ChooseAction(in AnimalContext context);
}

[Serializable]
internal sealed class Grazer : IAnimalBehavior
{
    [SerializeField, Range(0f, 1f)] private float _restShare = 0.5f;

    public AnimalAction ChooseAction(in AnimalContext context) =>
        context.Random01 < _restShare ? AnimalAction.Rest : AnimalAction.Graze;
}

[CreateAssetMenu(menuName = "Game/Animal")]
internal sealed class AnimalDefinition : ScriptableObject
{
    [SerializeReference] private IAnimalBehavior _behavior;

    public IAnimalBehavior Behavior => _behavior;
}
```

## Thousands of objects in arrays

A crowd of a thousand actors is data in arrays, updated by one system, with no object per actor. That is a performance choice, and it doesn't leave the architecture. Capabilities then sit at the system's boundary, and other domains see only those:

```csharp
public interface ICrowdPositions
{
    int Count { get; }
    Vector3 PositionOf(int actor);
}

public interface ICrowdOrders
{
    void WalkTo(int actor, Vector3 destination);
}

internal sealed class CrowdSystem : ICrowdPositions, ICrowdOrders, ITickable
{
    private Vector3[] _positions = new Vector3[1024];
    private Vector3[] _destinations = new Vector3[1024];

    public int Count { get; private set; }

    public Vector3 PositionOf(int actor) => _positions[actor];

    public void WalkTo(int actor, Vector3 destination) => _destinations[actor] = destination;

    public void Tick()
    {
        // Tight loops over the arrays: no interface calls per actor, no allocations.
    }
}
```

Where a hot loop must work over several kinds of data, a generic method with a struct constraint uses the interface with no boxing and no virtual call, because the runtime compiles it per struct:

```csharp
public interface IAdvancing
{
    void Advance(float deltaTime);
}

public struct WalkingActor : IAdvancing
{
    public float Phase;

    public void Advance(float deltaTime) => Phase += deltaTime;
}

public static class ActorUpdate
{
    public static void AdvanceAll<T>(T[] actors, int count, float deltaTime) where T : struct, IAdvancing
    {
        for (var i = 0; i < count; i++) actors[i].Advance(deltaTime);
    }
}
```

## Shortcuts to refuse

These are how a project drifts away from the architecture while every test stays green. Each comes from a real project, where 136 classes shared 6 interfaces and the audit later found 153 concrete dependencies.

| Shortcut | What it costs | Instead |
|---|---|---|
| Passing the whole simulation to every view (`new HudView(kit, layer, sim)`) | Every screen depends on everything, nothing can be tested or replaced | Narrow interfaces per reader: `IWallet`, `IVisitorStats`, `IFacilityQueries`; one class may implement them all at first |
| One director that owns every screen and system | A class that changes for every feature | Screens as their own entries, wired by the installer and messages |
| `new Service(...)` or `AddComponent` inside a service | Hidden dependency, no injection, no way to fake it | Register it; create objects through a typed factory |
| "It runs fast only with concrete types" | Usually unmeasured: an interface call costs nanoseconds | Measure first; the arrays section is the answer when it is true |
| "It's only a prototype" | Prototypes become the game | The same rules, with fewer features |

## Tests

Interfaces are what make logic testable without a scene: hand-written fakes implement them in Edit Mode tests, and the logic under test can't tell.
