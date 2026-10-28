# Providers

One piece of shared state with change notification: readers inject `IProvider<T>`, the owner injects `IProviderSetter<T>`.

- **Destination:** `Core/Providers/`
- **Depends on:** Logging; VContainer (registration helper only).

```csharp
// Installer: one Provider per state type, in the scope that matches the state's lifetime.
builder.RegisterProvider(new SelectionState(-1));

// Reader
_subscription = _selection.Subscribe(OnSelectionChanged);   // receives the current value first
// Dispose _subscription in Dispose() or OnDestroy().

// Owner
_selection.Set(new SelectionState(id));                      // notifies only on change
```

- `T` is a dedicated `readonly struct` implementing `IEquatable<T>`: with it, `Set` doesn't allocate.
- A subscriber that throws is logged and doesn't stop the others. A `Set` from inside a notification wins: every subscriber ends on the newest value.
- Main thread only.
