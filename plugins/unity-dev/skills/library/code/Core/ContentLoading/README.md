# ContentLoading

`AddressablesContentLoader : IContentLoader` loads Addressables assets and owns their handles.

- **Destination:** `Core/ContentLoading/`
- **Depends on:** Addressables, UniTask; VContainer.

```csharp
builder.Register<IContentLoader, AddressablesContentLoader>(Lifetime.Singleton);

var prefab = await _content.LoadAsync<GameObject>(_levelPrefab, cancellationToken);
var level = _resolver.Instantiate(prefab, _levelRoot);   // through the resolver for injection, under a parent
// ...when the level ends
Object.Destroy(level);
_content.Release(_levelPrefab);
```

- Instantiate with a parent or through a `ComponentFactory<T>`: the root scope's resolver alone would mark the instance `DontDestroyOnLoad` (see the DI module). Release the asset only after its last instance is destroyed.
- Don't use `Addressables.InstantiateAsync`: its instances get no injection.

- Every load needs a matching `Release`, after the load completes. Loading the same key twice shares one handle and needs two releases. Releasing more than was loaded throws.
- A failed or cancelled load releases its own reference and throws. Cancellation is checked once per frame, on the main thread, and a load sees its handle complete on the next frame at the latest.
- A key is loaded as one type; loading it as another type throws.
- `Dispose` (called by the container) releases everything loaded. Loads still running then end with `ObjectDisposedException` and release their handle themselves; `Release` after `Dispose` does nothing.
