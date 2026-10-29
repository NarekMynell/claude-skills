# Messaging and shared state

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

## MessagePipe

Message types:

```csharp
public readonly struct LevelCompleted
{
    public readonly int LevelIndex;
    public readonly float Time;

    public LevelCompleted(int levelIndex, float time)
    {
        LevelIndex = levelIndex;
        Time = time;
    }
}
```

Publishing and subscribing in a service:

```csharp
internal sealed class ProgressService : IStartable, IDisposable
{
    private readonly ISubscriber<LevelCompleted> _levelCompleted;
    private IDisposable _subscriptions;

    public ProgressService(ISubscriber<LevelCompleted> levelCompleted) => _levelCompleted = levelCompleted;

    public void Start()
    {
        var bag = DisposableBag.CreateBuilder();
        _levelCompleted.Subscribe(OnLevelCompleted).AddTo(bag);
        _subscriptions = bag.Build();
    }

    public void Dispose() => _subscriptions?.Dispose();

    private void OnLevelCompleted(LevelCompleted message) { }
}
```

In a MonoBehaviour, subscribe in `Start` or `OnEnable`, never in `Construct`, and bind the subscription to the object's lifetime with UniTask's extension: `_subscriber.Subscribe(OnSelected).AddTo(destroyCancellationToken);`. A pooled object disposes its subscriptions in `OnDespawned` instead.

- Inject `IPublisher<T>` / `ISubscriber<T>`. Async handlers use `IAsyncPublisher<T>` / `IAsyncSubscriber<T>`; `PublishAsync` runs them in parallel by default (`AsyncPublishStrategy`).
- Keyed channels (`IPublisher<TKey, T>`) only when receivers filter by a key such as a player id.
- Request/response between domains uses `IRequestHandler<TRequest, TResponse>` only when a direct interface call isn't possible. Request handlers are registered explicitly ([DI reference](dependency-injection.md#messagepipe-registration)).
- **Messages carry values, not ownership:** no disposables, pooled objects, native containers or Unity objects that can die before a handler runs.
- **A handler that throws** stops the handlers after it, and the exception reaches the publisher. Each handler deals with its own expected failures.
- **Leaks:** during development, check **Window > MessagePipe Diagnostics** for subscriptions that were never disposed. It needs `GlobalMessagePipe.SetProvider` in the root scope ([DI reference](dependency-injection.md#messagepipe-registration)). Stack traces of each subscription appear with `options.EnableCaptureStackTrace = true`, which slows subscribing: turn it on while hunting a leak, never in release builds.

## Providers

A Provider holds one piece of shared state and notifies subscribers when it changes. The library's Providers module implements it.

```csharp
public interface IProvider<T>
{
    T Value { get; }
    IDisposable Subscribe(Action<T> onChanged, bool notifyCurrentValue = true);
}

public interface IProviderSetter<T> : IProvider<T>
{
    void Set(T value);              // notifies only when the value changed
    void SetWithoutNotify(T value);
    void ForceNotify();
}
```

State type:

```csharp
public readonly struct SelectionState : IEquatable<SelectionState>
{
    public readonly int SelectedId;

    public SelectionState(int selectedId) => SelectedId = selectedId;

    public bool Equals(SelectionState other) => SelectedId == other.SelectedId;
    public override bool Equals(object obj) => obj is SelectionState other && Equals(other);
    public override int GetHashCode() => SelectedId;
}
```

- Readers inject `IProvider<T>`. Only the owner injects `IProviderSetter<T>`.
- Late subscribers receive the current value immediately (`notifyCurrentValue`).
- `Subscribe` returns an `IDisposable`: dispose it like any MessagePipe subscription. There is no `-=` to forget.
- Register each Provider with `builder.RegisterProvider(initialValue)` in the scope that matches the state's lifetime. App-wide state goes in the root scope.
- Without `IEquatable<T>`, the change check falls back to `EqualityComparer<T>.Default`, which boxes the struct and compares by reflection.
- If the project needs stream operators (filter, combine, throttle), the Providers implementation switches to R3 `ReactiveProperty<T>` behind the same interfaces.

## Choosing between a message and a Provider

- "It happened" → message. Late subscribers don't need it.
- "It is" → Provider. Anyone can read it at any time, and late subscribers need the current value.
- Never publish a message every frame to mirror a value. Read the Provider when needed.
