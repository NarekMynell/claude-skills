---
name: performance
description: Unity performance as a top priority - budgets, frame rate per platform, stopping work off screen, baked light with no runtime cost, static objects, mobile URP settings, draw calls and batching, crowds, memory and build size, thermals, Web, profiling on device.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# Unity performance

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

## Must

- **Optimization is a top priority, equal to beauty:** as beautiful and as cheap as possible. Neither excuses the other: the techniques of `game-design:art-direction` cost almost nothing, and that is the point of them.
- **Nothing is paid for that the player can't see:** what never moves is static, light that doesn't change is baked, work off screen stops, triangles and layers that never show are gone.
- **Budgets are set and measured:** `docs/performance-budgets.md`, from the start of the vertical slice (`game-design:game-design`, its production order) at the latest, with assumed devices marked as assumptions; checked at every milestone, on the target device or, until there is one, with numbers from the Frame Debugger and Profiler, and the report says which.
- **The proof:** [SceneCostAudit](../library/code/Core/Editor/CostChecks/README.md) clean, each exception with its reason; `OffScreenTests` and `BudgetTests` green, with their receipts.

Which technique reaches this is your decision, by thinking through this project: the sections below are options with their costs, not a recipe. Whatever you choose stays in the [architecture](../code-standards/SKILL.md#architecture): modular, behind interfaces, through DI.

**Principle.** Design for performance from the start: architecture, data layout, pooling, no allocations in per-frame code (those code rules are in the [code standards](../code-standards/SKILL.md)). Micro-optimize only from profiler data captured on the target device, and measure every optimization before and after.

## Budgets

The project records its budgets in `docs/performance-budgets.md`:

- target devices, including the minimum-spec device;
- the target frame rate and its frame time. On mobile, plan for about 65% of the frame (about 22 ms at 30 fps, 11 ms at 60 fps), so the device can stay cool under sustained load (Unity's profiling guide);
- memory, draw call and SetPass call budgets;
- build and download size.

Create the file when the target platforms are known. Check every milestone against it.

## Frame rate

The target is a per-project decision, recorded in the budgets: 60 fps for most action and touch-responsive games, 30 fps where the content and battery life allow it. Set it explicitly at startup (the library's Bootstrap module has a frame-rate step):

- **Android and iOS** render at a fixed 30 fps by default (`targetFrameRate = -1`), the usual reason an optimized mobile game runs at 30, and they ignore `vSyncCount`. Set `Application.targetFrameRate`. A value that doesn't divide the display's current refresh rate is rounded down to one that does: 60 on a 90 Hz screen gives 45 fps. For the display's native rate, use `Screen.currentResolution.refreshRateRatio`. On iOS, 120 Hz needs ProMotion enabled in the project. On Android, enable **Optimized Frame Pacing**.
- **Web.** Use `QualitySettings.vSyncCount = 1`, not `targetFrameRate`: on Web, `targetFrameRate` uses software timing and micro-stutters.
- **Desktop.** vSync on, or a target equal to the display's refresh rate.

The game holds its target on the minimum-spec device, sustained: run 10+ minutes to see thermal throttling.

## CPU

- Event-driven by default. Per-frame work runs in `ITickable` systems; non-critical logic runs every N frames; heavy work is spread across frames or moved to Burst jobs.
- Profile before guessing. The usual hotspots: per-frame allocations (GC spikes), `Update` methods on many objects, physics queries without layer masks, UI layout rebuilds, `Instantiate` / `Destroy` during gameplay, synchronous loading.
- Expensive custom code is wrapped in a `ProfilerMarker` so it shows up by name in the Profiler.

## Work the player can't see

Cheapest first; the choice depends on what the thing is and how many there are.

| Situation | Solution | Notes |
|---|---|---|
| Things that sway, spin, bob or flicker: trees, flags, lamps | Motion in the vertex shader, driven by time | No CPU at all, culled with the renderer, one material for thousands |
| Animators, skinned meshes, particles | Unity's own culling | `Animator.cullingMode`: Cull Update Transforms (root motion goes on, no bones or IK) or Cull Completely. `SkinnedMeshRenderer.updateWhenOffscreen` off. `ParticleSystem.main.cullingMode`: Pause, or Pause And Catch-up |
| Many similar objects with custom behavior | One `ITickable` system with arrays, skipping what's hidden | Update far things every Nth frame; distance bands below |
| An object with its own tween or script | `IPausable`, driven by the shared pauser | [Culling module](../library/code/Core/Culling/README.md) |

The last row, the way a project usually wires it: the component implements only `IPausable`, a `PauseWhenHidden` beside it receives `IVisibilityPauser` by injection, and one pauser and one `CullingGroup` serve the scene. Registered in an installer, faked in tests, unaware of cameras:

```csharp
public sealed class SwayingTree : MonoBehaviour, IPausable
{
    private Tween _sway;

    public void Pause() => _sway.Pause();

    public void Resume() => _sway.Play();
}
```

- **`CullingGroup`** tests bounding spheres, for one camera, against the view and static occlusion. Answers arrive asynchronously through `onStateChanged`. It reads your spheres array by reference, so moving a sphere is a write to the array. `SetBoundingDistances` with `SetDistanceReferencePoint` adds distance bands, ascending: full behavior near, reduced further, a simple rig far. Its owner calls `Dispose()`.
- **Not for this:** `Renderer.isVisible` and `OnBecameVisible` count the Scene view's camera, and shadow rendering too. Objects with `OnBecameVisible` or `OnBecameInvisible` also leave the GPU Resident Drawer.
- **DOTween:** `tween.Pause()`, `Play()` and `TogglePause()`; `SetLink` ties a tween to its object, and `LinkBehaviour.PauseOnDisableRestartOnEnable` handles disabled objects.
- **Off-screen logic** that matters, such as income, runs as simulation with no visuals: it never needs the view.

`OffScreenTests`, in the project's Play Mode tests, proves it on the real scene, with the camera turned to empty sky. It counts what moved, not only tweens: a sway written in a tick moves renderers too.

```csharp
[UnityTest]
public IEnumerator WithNothingInView_NothingWorks()
{
    gameCamera.transform.rotation = Quaternion.LookRotation(Vector3.up);
    yield return new WaitForSeconds(0.5f);

    var probe = new MovementProbe(sceneRoots);
    yield return new WaitForSeconds(1f);

    int moved = probe.Moved().Count;
    int playing = DOTween.TotalPlayingTweens();
    bool passed = moved <= allowedMovers && playing <= allowedTweens;
    ProofReceipt.Write("off-screen-main", passed, $"{moved} renderers moved and {playing} tweens played with nothing in view; {allowedMovers} and {allowedTweens} allowed");
    Assert.That(passed, $"{moved} renderers moved, {playing} tweens played");
}
```

The same scene in the Profiler shows the rest: with the camera on the sky, script and animation time drop to what the simulation needs. What doesn't drop is still working for nobody.

## Budgets as a test

`BudgetTests` holds the busiest view to the numbers in `docs/performance-budgets.md`, so a budget can fail, on every run. Frame time on the device stays with the Profiler.

```csharp
[UnityTest]
public IEnumerator TheBusiestView_StaysInBudget()
{
    using var drawCalls = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Draw Calls Count");
    using var setPasses = ProfilerRecorder.StartNew(ProfilerCategory.Render, "SetPass Calls Count");
    using var triangles = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Triangles Count");
    yield return null;
    yield return null;

    bool passed = drawCalls.LastValue <= budgetDrawCalls && setPasses.LastValue <= budgetSetPassCalls && triangles.LastValue <= budgetTriangles;
    ProofReceipt.Write("budgets-main", passed, $"{drawCalls.LastValue} draw calls, {setPasses.LastValue} SetPass calls, {triangles.LastValue} triangles");
    Assert.That(passed, $"{drawCalls.LastValue} draw calls, {setPasses.LastValue} SetPass calls, {triangles.LastValue} triangles");
}
```

## Light

The look comes first, and most of it can be baked. Cheapest first:

1. **Light in the asset:** `bake_light.py` (`modeling:models`) bakes Blender's light into vertex colors or a texture, then a simple shader draws it. Costs nothing per light at runtime, and lamps can glow at night through a shader global. The bake belongs to the asset, so shadows cast by its neighbors need a shared ground texture, or a bake after placement.
2. **Unity's lightmaps:** Baked lights, Progressive Lightmapper, a second UV set. Costs lightmap memory; Directional mode takes about twice Non-Directional's memory. URP's **Baked Lit** shader takes base map, normal map, alpha clip and GPU instancing, with no realtime light: Unity's mobile advice is Baked Lit for static objects and Simple Lit for moving ones on lower-end devices. Web supports baked GI with Non-Directional lightmaps only.
3. **What moves:** light probes (their main use), or a few shader globals for sun color and ambient, which also gives a day cycle for nothing. Adaptive Probe Volumes work in URP with per-vertex evaluation, but no page confirms mobile or Web: test before relying on them.
4. **Shadows of what moves:** a blob, or a planar shadow in the shader, far cheaper than a shadow map. A realtime shadow draws the scene again; Soft Shadows have a high impact on mobile. If realtime shadows are needed: Low soft quality, one main light, a short distance. Subtractive mixed lighting is the cheap mixed mode, Baked Indirect uses realtime shadow maps.

**Grading** through a LUT is among the cheapest big effects. From Unity 6.5, URP can run color grading, tonemapping, vignette, dithering and grain on-tile: integrated post-processing off, Tile-Only Mode on, the On Tile Post Processing renderer feature added. Tile-Only Mode gives up depth and opaque textures, MSAA, HDR, camera stacking and Deferred, and isn't supported on WebGL.

## Static

What never moves is marked static, per flag, on purpose. `SceneCostAudit` lists what looks static and isn't, and `NeverMovedProbe` names what stayed still through a real session, whatever scripts sit near it.

- **Batching Static** combines meshes (Mesh Renderers only, 64k vertices per buffer). See [repeated objects](#repeated-objects) for when it helps and when it doesn't.
- **Contribute GI** includes the renderer in baked lighting.
- **Occluder and Occludee** take part in occlusion culling; **Reflection Probe** in baked probes.
- **Navigation Static** is deprecated: use NavMesh Modifier with NavMesh Surface.
- Marking only what truly never moves: code that moves a static object fights the batch. A building that bounces when upgraded isn't static; its base can be.

## Rendering

- **Shaders** are as simple as the look allows, and SRP Batcher compatible. Strip unused variants. `discard` and `clip` hurt early depth tests: use alpha clip only where needed.
- **Effects, cheapest first:** a shader on the object's material → a renderer feature written for Render Graph → full-screen post-processing. Choose the cheapest that achieves the look.
- **Mobile URP settings,** by Unity's advice for better performance: HDR off; MSAA reduced or off; Depth Texture and Opaque Texture off unless needed (on devices without StoreAndResolve, MSAA is ignored with Opaque Texture on); Depth Priming off on mobile; Store Actions Auto or Discard; Intermediate Texture Auto; Render Scale below 1, since the UI stays at native resolution; few realtime lights; mobile-friendly post only: Bloom without High Quality Filtering, Chromatic Aberration, Color Grading, Lens Distortion, Vignette. Forward+ removes the per-object light limit, with up to 32 lights per camera on mobile. Measure each change.
- **Overdraw:** transparent layers, particles and full-screen passes are the classic mobile cost.
- **LODs** for 3D objects seen at a distance: authored `_LODn` meshes in a LOD Group when the levels differ in materials or renderer settings; Mesh LOD (generated on import, in recent Unity 6 versions) for geometry-only reduction with less memory. Never both on one model. Particle Systems, VFX Graph and static batching always draw LOD0 of a Mesh LOD.
- Occlusion culling in enclosed scenes.

### Repeated objects

Objects that share a mesh and differ in position, rotation, scale or color, such as props, trees, rocks or modular pieces, are one asset placed many times, never unique meshes and never one mesh merged by hand. How Unity 6 URP draws them cheaply:

- **SRP Batcher** on, always. It batches by shader variant, so different materials on the same shader batch together. **Material Variants** of one material give each look its own material at almost no cost.
- **Per-object values** (a tint, a palette index): a per-renderer value through `SetShaderUserValue` on `MeshRenderer` or `SkinnedMeshRenderer`, read in the shader, which keeps one material and doesn't interfere with batching (in the Unity 6.6 documentation; check the project's version). No `MaterialPropertyBlock` in URP: Unity advises against it, and it takes the renderer out of the SRP Batcher and the GPU Resident Drawer.
- **GPU Resident Drawer** for scenes with many objects sharing meshes and shader variants. It needs the Forward+ or Deferred+ path, **BatchRendererGroup Variants: Keep All** (longer builds) and the SRP Batcher, and doesn't run on OpenGL ES. It skips objects with a `MaterialPropertyBlock`, objects under an Animator or Animation, and scripts with `OnWillRenderObject`, `OnBecameVisible` or `OnBecameInvisible`. It saves CPU but adds GPU work, so a GPU-bound mobile game can get slower: keep it only when the Profiler on the target device shows a gain (Unity 6.6 reports its coverage).
- **Static batching** isn't compatible with the GPU Resident Drawer, and it stores a combined copy of every instance's mesh, which multiplies memory for repeated meshes. Use it only where the GPU Resident Drawer can't run, such as OpenGL ES devices, and only when profiling there shows a gain. Dynamic batching is obsolete in Unity 6.6.
- **The material's GPU Instancing checkbox** stays off with the SRP Batcher and the GPU Resident Drawer (it only adds shader variants), except on materials drawn with `Graphics.RenderMeshInstanced`, which need it.
- **Thousands of instances with no behavior of their own** (grass, debris, distant crowds): no GameObject per instance. Terrain details and trees for terrain vegetation; otherwise `Graphics.RenderMeshInstanced`, submitted per spatial chunk, because each call is culled as one bounding box. `BatchRendererGroup` only for advanced cases.
- **Combining meshes by hand** only for static parts that sit close together and never move relative to each other, per spatial chunk (a room, a block), never across a level: a combined mesh is culled, lit and LODed as one object and can't be instanced. Profile before and after.

## Crowds and many animated objects

- **An Animator per actor** costs CPU per actor, and no official numbers exist: measure. It helps to use `Optimize Game Objects` on the model, the culling modes above, `QualitySettings.skinWeights` lowered per quality level, and simpler rigs and fewer updates far away through distance bands.
- **Baked animation in a shader,** vertex or bone textures, draws hundreds of actors in one call. No official guidance exists, GPU instancing needs Mesh Renderers, so it means leaving Animators behind: write the checks' bridge too ([animation](../animation/SKILL.md)), or nobody knows if its motion is good.
- **Choosing:** count the actors the balance simulation predicts at peak on the minimum device, then the cheapest option that keeps the motion's quality. Decide by a test scene with those numbers.

## Battery and thermals

- A game that holds its frame rate while hot is the goal: 10+ minutes on the device shows it.
- **Menus and idle screens** don't need full rate: `OnDemandRendering.renderFrameInterval` skips rendering while input and logic keep running (0 or 1 restores it; high values feel unresponsive), or a lower `Application.targetFrameRate`.
- **Adaptive Performance** is built into Unity since 6.3; the package now holds only samples and Visual Scripting units.

## Web

- C# threads aren't available. Native and Burst threads need **Enable Native C/C++ Multithreading** and the COOP, COEP and CORP headers on the server.
- Set **Initial Memory Size** for mobile browsers; the garbage collector runs only at the end of a frame, so allocation spikes hit harder here.
- gzip by default; Brotli compresses best and needs HTTPS in Chrome and Firefox. The server sets `Content-Encoding`.
- WebGL2 is the default; WebGPU has to be added to the graphics APIs by hand, and has limited browser and device support.
- Build size and more: the official `unity:optimize-web` skill.

## Memory

- **Textures:** size and compression set per platform (ASTC on mobile), mipmaps on 3D textures, none on UI. Data textures (normal, mask, metallic, smoothness) have sRGB off; normal maps use the Normal Map texture type.
- **Meshes:** **Read/Write** off unless the CPU reads the mesh: code, a Mesh Collider, a Particle System's Shape module (or its Renderer without GPU instancing) or a Terrain detail. Turn it on for those yourself. Unity 6000.6.2f1 still handles them during the build, with a warning that future versions won't (seen once in a build); its documentation already says the build fails. Treat that warning as an error. Mesh Collider meshes also get pre-baked collision: [models](../models/SKILL.md#import-settings).
- **Mesh Compression** only shrinks the files on disk. It costs load time, can create artifacts, and turns off vertex compression for that mesh. Runtime mesh memory is set by **Vertex Compression** in Player Settings, whose defaults suit most projects.
- Audio import settings: the official `unity:optimize-audio` skill.
- Every Addressables load has a matching release. Check for leaks with Memory Profiler snapshots taken before and after a level, as the [resource lifetimes](../code-standards/references/resource-lifetimes.md#finding-leaks) rules describe.

## Sprite atlases

- One sprite from an atlas keeps the **whole atlas texture** in memory.
- Group sprites by what is on screen together: a screen, a level, a character. Shared UI goes in one common atlas. Never pack unrelated content into one big atlas.
- With Addressables, make the SpriteAtlas itself Addressable; otherwise its texture is duplicated into every bundle that uses its sprites.
- Master and variant atlases and prebuild packing: the official `unity:manage-sprite-atlas` skill.

## Profiling

- Profile a **development build on the target device**, not the Editor. Editor numbers include Editor overhead and a different GPU.
- Tools: Profiler (CPU, GPU, memory, GPU Resident Drawer), Frame Debugger (draw calls, SetPass calls, batching breaks), Memory Profiler (snapshots, leaks), Profile Analyzer (before/after comparison), Project Auditor (code and settings).
- Record the result of each optimization (metric before, after, device) in the change description.

## Build size

- Managed code stripping as high as the project tolerates. Code that relies on reflection is protected with `link.xml`.
- Remove unused packages and assets. Read the build report after every release build.

## Sources

From Unity's manual and scripting reference for 6000.6: [configuring URP for performance](https://docs.unity.com/en-us/engine/6000.6/manual/render-pipelines/universal-render-pipeline/introduction/configure-for-better-performance), [optimizing URP](https://docs.unity.com/en-us/engine/6000.6/manual/analysis/graphics-performance-profiling/in-urp/optimize-for-better-performance), [Baked Lit](https://docs.unity.com/en-us/engine/6000.6/manual/materials-and-shaders/built-in/shaders-in-universalrp/reference/baked-lit-shader), [lightmaps](https://docs.unity.com/en-us/engine/6000.6/manual/lighting-overview/direct-and-indirect-lighting/lightmapping/baking-before-runtime/lightmaps-reference), [lighting modes](https://docs.unity.com/en-us/engine/6000.6/manual/lighting-overview/lighting-light-sources/components/configuring/lighting-mode/lighting-mode), [on-tile rendering](https://docs.unity.com/en-us/engine/6000.6/manual/analysis/graphics-performance-profiling/in-urp/on-tile-rendering), [on-tile post-processing](https://docs.unity.com/en-us/engine/current/manual/post-processing-and-full-screen-effects/urp/on-tile-post-processing), [CullingGroup](https://docs.unity.com/en-us/engine/6000.6/manual/cameras/occlusion-culling/culling-group-api/api), [static objects](https://docs.unity.com/en-us/engine/6000.6/manual/working-with-gameobjects/gameobject-fundamentals/static-objects), [OnDemandRendering](https://docs.unity.com/en-us/engine/6000.6/script-reference/unityengine/rendering/ondemandrendering), [Web memory](https://docs.unity.com/en-us/engine/6000.6/manual/platform-specific/webgl/develop/memory). [DOTween](https://dotween.demigiant.com/documentation.php). Check them for the project's version.
