# Culling

`VisibilityPauser` pauses `IPausable` targets while their bounding sphere is outside the camera's view, with one `CullingGroup` for all of them.

- **Destination:** `Core/Culling/`
- **Depends on:** Lifecycle, Extensions, Logging.

```csharp
_pauser = new VisibilityPauser(camera);
_pauser.Register(enemy, enemy.Position, radius: 1.5f);
_pauser.UpdatePosition(enemy, enemy.Position);   // for moving targets, from the system that moves them
_pauser.Unregister(enemy);
_pauser.Dispose();
```

- Use Unity's built-in culling first (Animator and particle culling modes); this is for custom per-frame behaviour.
- A newly registered target starts paused until the first culling pass reports it visible.
- `Unregister` and `Dispose` resume a paused target, so nothing stays paused for good. Destroyed targets are skipped.
- An exception from a target's `Pause` or `Resume` is logged and stops nothing else: not the other targets of a culling pass, not `Unregister`, not `Dispose`.
- The pauser owns a `CullingGroup`, a native object: its owner disposes it. A second `Dispose` does nothing; `Register` and `UpdatePosition` afterwards throw `ObjectDisposedException`, and `Unregister` does nothing.
