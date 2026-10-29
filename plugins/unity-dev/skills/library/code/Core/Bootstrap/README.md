# Bootstrap

The startup flow of the Bootstrap scene (build index 0).

- **Destination:** `Core/Bootstrap/` and `Core/Editor/Bootstrap/`
- **Depends on:** Providers, Scenes, Serialization, Logging; VContainer, UniTask.

```csharp
// Root or Bootstrap scope installer, steps in the order they run:
builder.RegisterInstance(_frameRateConfig);
builder.RegisterInstance(_firstSceneConfig);
builder.Register<IBootstrapStep, FrameRateStep>(Lifetime.Singleton);
builder.Register<IBootstrapStep, LoadSavesStep>(Lifetime.Singleton);       // project steps
builder.Register<IBootstrapStep, LoadFirstSceneStep>(Lifetime.Singleton);  // always last
builder.RegisterBootstrapFlow();
```

- `BootstrapFlow` runs the steps in order and publishes `IProvider<BootstrapProgress>` (status and overall 0–1 progress) for the loading screen. A failing step is logged and stops the startup with status `Failed`; so does a step that cancels itself, such as a timeout. Only the scope's own shutdown counts as cancellation, and it ends the startup quietly, without logging.
- Register the flow in the root scope or in the Bootstrap scene's scope: it completes even when its last step replaces the scene that holds it.
- **Typical steps:** frame rate and quality, DOTween init, Addressables init and preload, saves and settings, app services (audio, localization, analytics), pool and shader warm-up, then the first scene.
- `FrameRateStep` + `FrameRateConfig`: mobile gets no vSync and an explicit target (Unity's mobile default is 30 fps), Web gets vSync (software timing micro-stutters there), desktop gets vSync.
- `LoadFirstSceneStep` + `FirstSceneConfig` opens the first scene. In the Editor it opens the scene that was open when Play was pressed instead.
- **Play from Bootstrap** (Editor): Play always starts from the first enabled scene of the active Build Profile, saving modified scenes first. Play Mode test runs are left alone. Turn it off in **Tools > Company.Product > Play From Bootstrap**, per user and project.
- Keep the Bootstrap scene tiny: a camera, a loading screen with small assets, and the scope. Something is on screen on the first frame.
