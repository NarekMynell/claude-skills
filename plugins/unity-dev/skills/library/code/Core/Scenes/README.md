# Scenes

- **Destination:** `Core/Scenes/`
- **Depends on:** UniTask.

`SceneLoader : ISceneLoader` starts loading the scene in the background, shows an `ISceneTransition`, reports progress, activates the scene, then hides the transition.

```csharp
builder.Register<ISceneTransition, FadeTransition>(Lifetime.Singleton);   // or NoSceneTransition
builder.Register<ISceneLoader, SceneLoader>(Lifetime.Singleton);

await _sceneLoader.LoadAsync(_levelScene.ScenePath, progress, cancellationToken);
```

- Scenes are referenced by path; use `SceneReference` in configs.
- The transition must survive the load: implement it in the root scope's prefab.
- In the Editor, a scene outside the Build Profile's list still loads, so any scene can be played; in builds it must be in the list.
- An invalid path throws before the transition shows.
- The transition is hidden however the load ends.
- A load can't be aborted. Once activation starts, the load finishes even if the caller's scope is destroyed by the new scene. If the token is cancelled earlier, the scene still activates (a load held back would block every later load), and then the cancellation is thrown.
