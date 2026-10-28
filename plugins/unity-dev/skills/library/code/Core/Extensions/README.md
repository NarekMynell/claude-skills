# Extensions

Small, allocation-free helpers, one static class per extended type.

- **Destination:** `Core/Extensions/`
- **Depends on:** nothing.

| Method | Purpose |
|---|---|
| `IsAlive()`, `OrNull()` | Liveness check that sees Unity's destroyed state through interface references: `damageable.OrNull()?.TakeDamage(1)` |
| `SafeDestroy()` | `Destroy` in Play Mode, `DestroyImmediate` in Edit Mode |
| `Transform.ResetLocal()`, `DestroyChildren()` | Transform housekeeping |
| `GameObject.SetLayerRecursively()` | Layer for a whole hierarchy |
| `WithX/WithY/WithZ`, `ToXZ`, `FromXZ` | Vector component edits |
| `Color.WithAlpha()` | Colour with another alpha |
| `List.SwapRemoveAt()` | O(1) removal when order doesn't matter |

Never use `== null` or `?.` on an interface that can point to a `UnityEngine.Object`: use `IsAlive()` or `OrNull()`.
