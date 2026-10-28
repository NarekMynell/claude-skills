# ContentLoading

`AddressablesContentLoader : IContentLoader` loads Addressables assets and owns their handles.

- **Destination:** `Core/ContentLoading/`
- **Depends on:** Addressables, UniTask (with `UniTask.Addressables`); VContainer.

```csharp
builder.Register<IContentLoader, AddressablesContentLoader>(Lifetime.Singleton);

var prefab = await _content.LoadAsync<GameObject>(_levelPrefab, cancellationToken);
var level = _resolver.Instantiate(prefab);   // instantiate through the resolver for injection
// ...when the level ends
_content.Release(_levelPrefab);
```

- Every load needs a matching `Release`, after the load completes. Loading the same key twice shares one handle and needs two releases. Releasing more than was loaded throws.
- A failed or cancelled load releases its own reference and throws.
- A key is loaded as one type; loading it as another type throws.
- `Dispose` (called by the container) releases everything loaded. Loads still running then end with `ObjectDisposedException` and release their handle themselves; `Release` after `Dispose` does nothing.
