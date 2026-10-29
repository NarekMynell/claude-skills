# Scenes

- **Destination:** `Core/Scenes/`
- **Depends on:** UniTask.

`SceneLoader : ISceneLoader` shows an `ISceneTransition`, loads the scene while reporting progress, then hides the transition.

```csharp
builder.Register<ISceneTransition, FadeTransition>(Lifetime.Singleton);   // or NoSceneTransition
builder.Register<ISceneLoader, SceneLoader>(Lifetime.Singleton);

await _sceneLoader.LoadAsync(_levelScene.ScenePath, progress, cancellationToken);
```

- Scenes are referenced by path; use `SceneReference` in configs.
- The transition and the progress receiver must survive the load: implement them in the root scope's prefab.
- In the Editor, a scene outside the Build Profile's list still loads, so any scene can be played; in builds it must be in the list.
- An invalid path throws before the transition shows. A second load before the first has returned, including while its transition hides, throws `InvalidOperationException`: start the next load once `LoadAsync` has returned, for example from the code that awaited it.
- The load starts once the transition covers the screen, and the scene activates as soon as it has loaded. Activation is never held back: a held load stalls every other `AsyncOperation`, including asset loads a transition or loading screen might wait for.
- **Cancellation** stops the load only before it starts: then `LoadAsync` throws `OperationCanceledException` and nothing loads. Once started, the load finishes and `LoadAsync` returns normally, also when the new scene destroys the caller's scope.
- The transition is hidden however the load ends.
