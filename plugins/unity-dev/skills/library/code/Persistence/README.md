# Persistence

Versioned JSON saves that survive crashes and power loss.

- **Destination:** `Persistence/` (its own domain)
- **Depends on:** Newtonsoft JSON (`com.unity.nuget.newtonsoft-json`), UniTask; VContainer.

```csharp
// Root scope installer
builder.RegisterFileSaveStorage();
builder.RegisterJsonSave(new SaveSchema<ProgressData>("progress", currentVersion: 2,
    new ISaveMigration[] { new ProgressV1ToV2() }));

var progress = await _saves.LoadAsync(cancellationToken) ?? new ProgressData();
await _saves.SaveAsync(progress, cancellationToken);
```

- Saves are `{ "version": N, "data": { ... } }`. Loading runs each `ISaveMigration` (it edits the JSON from `FromVersion` to the next version) up to the current version, and refuses a save from a newer build.
- **Crash-safe files.** `FileSaveStorage` writes under `persistentDataPath/Saves`: the data goes to a temporary file that is flushed to disk, the current save becomes `<key>.sav.bak`, and the temporary file takes its place. Each file starts with a 12-byte header (its length and a CRC-32), followed by the JSON. A read returns the newest intact copy, the save or else its backup, and repairs a damaged save from the backup. Files without the header, written by an earlier version of the module, are read as they are.
- **Order and threads.** File work runs on the thread pool (inline on Web), one operation at a time in start order, so two saves in one frame can't interleave and the later one wins. It never waits for the main thread. A cancellation token is checked when an operation starts; a started write always finishes. Register one storage per directory.
- **Save when the app pauses.** On mobile, `OnApplicationQuit` isn't called on iOS and the OS may kill a paused app without warning, so save on pause and focus loss. A root-scope component forwards the callback; `Flush` blocks until the started writes are on disk:

  ```csharp
  private void OnApplicationPause(bool paused)
  {
      if (!paused) return;

      _saves.SaveAsync(_progress.ToSaveData(), CancellationToken.None).Forget();
      _storage.Flush(TimeSpan.FromSeconds(2));
  }
  ```

  Disposing the storage, which the container does on quit, waits for pending writes the same way.
- **Web.** Files in `persistentDataPath` persist between visits only when the Web template's config sets `autoSyncPersistentDataPath: true`.
- **IL2CPP.** Newtonsoft reaches the DTOs through reflection, so stripping can remove their constructors and property setters. `[Preserve]` on a type keeps only the type and its default constructor: keep the DTOs with a `link.xml` entry that preserves them entirely (`<type fullname="MyGame.Saves.*" preserve="all"/>`).
- Save data is plain DTO classes. Serialization runs on the calling thread when `SaveAsync` is called, so the save holds the data as it was then; only the file work leaves the main thread.
- The serializer ignores `JsonConvert.DefaultSettings`, so another plugin's global settings can't change the save format or make a save choose the types it loads.
- Strings that look like dates load exactly as saved.
- Keys contain only letters, digits, `-` and `_`.
