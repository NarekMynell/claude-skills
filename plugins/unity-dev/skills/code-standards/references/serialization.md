# Serialization and saving

## Interfaces in the Inspector

Unity can't serialize a field whose type is an interface.

- **`SerializedInterface<T>`** (library, Serialization module) references a `UnityEngine.Object` that implements `T`: a MonoBehaviour or a ScriptableObject. Its drawer accepts only matching objects; dropping a GameObject picks its matching component. `Value` returns `null` for destroyed objects.

  ```csharp
  [SerializeField] private SerializedInterface<IDamageable> _target;
  ```

- **`[SerializeReference]`** stores a plain C# object by its runtime type, for polymorphic data such as strategies or steps inside a config. Unity has no built-in type picker for it: add the library's `[SubclassSelector]`. Renaming or moving such a type breaks existing data unless it carries `[MovedFrom]`.

## Save data

- **Its own domain.** Saving sits behind `ISaveService<T>` and `ISaveStorage`, registered in DI; the library's Persistence module implements both (`JsonSaveService<T>`, `FileSaveStorage`). Swapping the format or the storage doesn't touch callers.
- **Format by need:**

  | Need | Format |
  |---|---|
  | Default: readable, debuggable, flexible | JSON through Newtonsoft (`com.unity.nuget.newtonsoft-json`) |
  | Large data, frequent saves, size or speed critical | MessagePack-CSharp, with AOT-generated formatters for IL2CPP |
  | Small flat data at maximum speed, no dictionaries or polymorphism | `JsonUtility` |

- **DTOs.** Save data is plain data types, mapped to and from runtime state by the persistence domain. Runtime objects are never serialized directly.
- **Versioning.** Every save carries a schema version. Loading migrates older versions forward, one step per version.
- **Atomic writes.** Write to a temporary file, then replace the old one, so a crash mid-save never corrupts the existing save.
- **Never block a frame on file I/O.** Run it off the main thread where the platform allows. Web has no threads: keep saves small there.
- **IL2CPP.** Types serialized through reflection are kept with `[Preserve]` or `link.xml`.
- Never `BinaryFormatter`: insecure and obsolete. `PlayerPrefs` only for small device-local preferences.
