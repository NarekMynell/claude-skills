# Serialization

Inspector serialization that Unity lacks.

- **Destination:** `Core/Serialization/` and the drawers in `Core/Editor/Serialization/`
- **Depends on:** nothing.

| Type | Use |
|---|---|
| `SerializedInterface<T>` | A field for a MonoBehaviour or ScriptableObject that implements `T`. Dropping a GameObject picks its matching component. `Value` is `null` for destroyed objects. |
| `[SubclassSelector]` | Adds a type dropdown to a `[SerializeReference]` field, listing concrete `[Serializable]` classes with a parameterless constructor from assemblies that exist in builds |
| `SerializableDictionary<TKey, TValue>` | Inspector-edited, read-only at runtime. Repeated, null and empty-string keys are skipped and counted in `InvalidEntryCount` |
| `SceneReference` | A scene picked as an asset, stored as its path; the path follows renames when the owner is saved |

```csharp
[SerializeField] private SerializedInterface<IDamageable> _target;
[SerializeReference, SubclassSelector] private IEnemyBehaviour _behaviour;
[SerializeField] private SerializableDictionary<string, int> _prices;
[SerializeField] private SceneReference _menuScene;

private void OnValidate()
{
    if (_prices.InvalidEntryCount > 0) Debug.LogWarning($"{name}: repeated or empty price keys.", this);
}
```

Renaming or moving a class used with `[SerializeReference]` needs `[MovedFrom]`, or existing data is lost.
