# Culling

`IVisibilityPauser` pauses `IPausable` targets while their bounding sphere is outside the camera's view, with one `CullingGroup` for all of them. `PauseWhenHidden` connects any object to it with no code of its own.

- **Destination:** `Core/Culling/`
- **Depends on:** Lifecycle, Extensions, Logging; VContainer.

Register one pauser in the scene's installer:

```csharp
builder.RegisterVisibilityPauser(_camera);
```

A component says what pausing means for it, and a `PauseWhenHidden` on the same object (with a radius that covers it, and injection, like any scene object or factory-made object) does the rest:

```csharp
public sealed class SwayingTree : MonoBehaviour, IPausable
{
    private Tween _sway;

    public void Pause() => _sway.Pause();

    public void Resume() => _sway.Play();
}
```

A system that handles its objects itself calls the pauser directly:

```csharp
_pauser.Register(enemy, enemy.Position, radius: 1.5f);
_pauser.UpdatePosition(enemy, enemy.Position);   // for moving targets, from the system that moves them
_pauser.Unregister(enemy);
```

- Use Unity's built-in culling first (Animator and particle culling modes), and shader-driven motion where it fits, which costs no CPU at all. This is for custom behavior: [choosing](../../../../performance/SKILL.md#work-the-player-cant-see).
- A newly registered target starts paused until the first culling pass reports it visible.
- `Unregister` and `Dispose` resume a paused target, so nothing stays paused for good. Destroyed targets are skipped.
- An exception from a target's `Pause` or `Resume` is logged and stops nothing else: not the other targets of a culling pass, not `Unregister`, not `Dispose`.
- `CullingGroup` works for one camera, tests spheres against the view and static occlusion, and answers asynchronously. The Scene view camera doesn't count, unlike `Renderer.isVisible`.
- The pauser owns a `CullingGroup`, a native object: its owner disposes it (the container does when it was registered as above). A second `Dispose` does nothing; `Register` and `UpdatePosition` afterwards throw `ObjectDisposedException`, and `Unregister` does nothing.

`MovementProbe` names the renderers that moved since it was created, whatever moved them. With the camera on empty sky, what moved is work nobody saw: the [performance guide](../../../../performance/SKILL.md#work-the-player-cant-see) has the test.
