# Logging

`Log.Debug` for development diagnostics, compiled out of release builds; `Log.Warning`, `Log.Error` and `Log.Exception` always log.

- **Destination:** `Core/Logging/`
- **Depends on:** nothing.

```csharp
Log.Debug($"Spawned {count} enemies", this);   // removed with its argument in release builds
Log.Exception(exception, this);
```

`Debug` is marked `[Conditional("UNITY_EDITOR"), Conditional("DEVELOPMENT_BUILD")]`, so the call and the string it builds disappear from release builds.
