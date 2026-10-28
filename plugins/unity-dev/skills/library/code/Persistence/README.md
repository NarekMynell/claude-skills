# Persistence

Versioned JSON saves with crash-safe writes.

- **Destination:** `Persistence/` (its own domain)
- **Depends on:** Newtonsoft JSON (`com.unity.nuget.newtonsoft-json`), UniTask; VContainer.

```csharp
builder.Register<ISaveStorage, FileSaveStorage>(Lifetime.Singleton);
builder.RegisterInstance(new SaveSchema<ProgressData>("progress", currentVersion: 2,
    new ISaveMigration[] { new ProgressV1ToV2() }));
builder.Register<ISaveService<ProgressData>, JsonSaveService<ProgressData>>(Lifetime.Singleton);

var progress = await _saves.LoadAsync(cancellationToken) ?? new ProgressData();
await _saves.SaveAsync(progress, cancellationToken);
```

- Saves are `{ "version": N, "data": { ... } }`. Loading runs each `ISaveMigration` (it edits the JSON from `FromVersion` to the next version) up to the current version, and refuses a save from a newer build.
- `FileSaveStorage` writes under `persistentDataPath/Saves`. The new data goes to a temporary file, the old save becomes a backup, the temporary file takes its place, then the backup is deleted; a read after a crash restores the backup. File work runs on the thread pool (inline on Web), one operation at a time in start order, so two saves in one frame can't interleave and the later one wins. Register one storage per directory.
- Strings that look like dates load exactly as saved.
- Keys contain only letters, digits, `-` and `_`.
- Save data is plain DTO classes. Serialize on the main thread; only the file work leaves it.
- IL2CPP: keep the DTO types with `[Preserve]` or `link.xml`, since Newtonsoft reaches them through reflection.
