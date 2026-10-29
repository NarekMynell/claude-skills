# Serialization and saving

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

## Interfaces in the Inspector

Unity can't serialize a field whose type is an interface.

- **`SerializedInterface<T>`** (library, Serialization module) references a `UnityEngine.Object` that implements `T`: a MonoBehaviour or a ScriptableObject. Its drawer accepts only matching objects; dropping a GameObject picks its matching component. `Value` returns `null` for destroyed objects.

  ```csharp
  [SerializeField] private SerializedInterface<IDamageable> _target;
  ```

- **`[SerializeReference]`** stores a plain C# object by its runtime type, for polymorphic data such as strategies or steps inside a config. Unity has no built-in type picker for it: add the library's `[SubclassSelector]`. Renaming or moving such a type breaks existing data unless it carries `[MovedFrom]`.

## Save data

- **Its own domain.** Saving sits behind `ISaveService<T>` and `ISaveStorage`, registered in DI; the library's Persistence module implements both (`RegisterJsonSave<T>()`, `RegisterFileSaveStorage()`). Swapping the format or the storage doesn't touch callers.
- **Format by need:**

  | Need | Format |
  |---|---|
  | Default: readable, debuggable, flexible | JSON through Newtonsoft (`com.unity.nuget.newtonsoft-json`) |
  | Large data, frequent saves, size or speed critical | MessagePack-CSharp, with AOT-generated formatters for IL2CPP |
  | Small flat data at maximum speed, no dictionaries or polymorphism | `JsonUtility` |

- **DTOs.** Save data is plain data types, mapped to and from runtime state by the persistence domain. Runtime objects are never serialized directly.
- **Versioning.** Every save carries a schema version. Loading migrates older versions forward, one step per version.
- **Crash-safe writes.** Write to a temporary file and flush it to disk, keep the previous save as a backup, then move the new file into place. Check each file's integrity (length and checksum) on read and fall back to the backup, so neither a crash mid-save nor a power loss can cost more than the save in progress.
- **Save at the right moments:** after meaningful progress (a level end, a purchase, a checkpoint) and whenever the app pauses or loses focus (`OnApplicationPause(true)`, `OnApplicationFocus(false)`). On mobile, `OnApplicationQuit` and `OnDestroy` may never run: iOS suspends apps instead of quitting them, and the OS can kill a suspended app. A save started on pause must finish without the main thread, which stops while the app is in the background.
- **Never block a frame on file I/O.** Run it off the main thread where the platform allows. The exception is the pause callback, which waits for pending writes, since no frame follows. Web has no threads: keep saves small there.
- **Web** persists `persistentDataPath` between visits only when the Web template's config sets `autoSyncPersistentDataPath: true`.
- **IL2CPP.** Types serialized through reflection must survive managed code stripping. `[Preserve]` on a type keeps only the type and its default constructor, not its properties: keep DTOs with a `link.xml` that preserves them entirely (`preserve="all"`, or a namespace wildcard).
- Never `BinaryFormatter`: insecure and obsolete. `PlayerPrefs` only for small device-local preferences.
