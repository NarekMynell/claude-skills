---
name: performance
description: Unity performance standards and optimization - budgets, frame rate per platform, CPU, GPU, memory and build size, draw calls and batching, repeated objects, sprite atlases, textures, LODs, profiling on device.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# Unity performance

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

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

## Rendering

- **Shaders** are as simple as the look allows, and SRP Batcher compatible. Strip unused variants.
- **Effects, cheapest first:** a shader on the object's material → a renderer feature written for Render Graph → full-screen post-processing. Choose the cheapest that achieves the look.
- **Mobile:** control overdraw (transparent layers, particles, full-screen passes); bake lighting; few realtime lights and shadows; minimal post-processing.
- **LODs** for 3D objects seen at a distance: authored `_LODn` meshes in a LOD Group when the levels differ in materials or renderer settings; Mesh LOD (generated on import, in recent Unity 6 versions) for geometry-only reduction with less memory. Never both on one model. Particle Systems, VFX Graph and static batching always draw LOD0 of a Mesh LOD.
- Occlusion culling in enclosed scenes.

### Repeated objects

Objects that share a mesh and differ in position, rotation, scale or color, such as props, trees, rocks or modular pieces, are one asset placed many times, never unique meshes and never one mesh merged by hand. How Unity 6 URP draws them cheaply:

- **SRP Batcher** on, always. It batches by shader variant, so different materials on the same shader batch together. **Material Variants** of one material give each look its own material at almost no cost.
- **Per-object values** (a tint, a palette index): a per-renderer value through `Renderer.SetShaderUserValue`, read in the shader, which keeps one material and doesn't interfere with batching (in the Unity 6.6 documentation; check the project's version). No `MaterialPropertyBlock` in URP: Unity advises against it, and it takes the renderer out of the SRP Batcher and the GPU Resident Drawer.
- **GPU Resident Drawer** for scenes with many objects sharing meshes and shader variants. It needs the Forward+ or Deferred+ path, **BatchRendererGroup Variants: Keep All** (longer builds) and the SRP Batcher, and doesn't run on OpenGL ES. It skips objects with a `MaterialPropertyBlock`, objects under an Animator or Animation, and scripts with `OnWillRenderObject`, `OnBecameVisible` or `OnBecameInvisible`. It saves CPU but adds GPU work, so a GPU-bound mobile game can get slower: keep it only when the Profiler on the target device shows a gain (Unity 6.6 reports its coverage).
- **Static batching** isn't compatible with the GPU Resident Drawer, and it stores a combined copy of every instance's mesh, which multiplies memory for repeated meshes. Use it only where the GPU Resident Drawer can't run, such as OpenGL ES devices, and only when profiling there shows a gain. Dynamic batching is obsolete in Unity 6.6.
- **The material's GPU Instancing checkbox** stays off with the SRP Batcher and the GPU Resident Drawer (it only adds shader variants), except on materials drawn with `Graphics.RenderMeshInstanced`, which need it.
- **Thousands of instances with no behavior of their own** (grass, debris, distant crowds): no GameObject per instance. Terrain details and trees for terrain vegetation; otherwise `Graphics.RenderMeshInstanced`, submitted per spatial chunk, because each call is culled as one bounding box. `BatchRendererGroup` only for advanced cases.
- **Combining meshes by hand** only for static parts that sit close together and never move relative to each other, per spatial chunk (a room, a block), never across a level: a combined mesh is culled, lit and LODed as one object and can't be instanced. Profile before and after.

## Memory

- **Textures:** size and compression set per platform (ASTC on mobile), mipmaps on 3D textures, none on UI. Data textures (normal, mask, metallic, smoothness) have sRGB off; normal maps use the Normal Map texture type.
- **Meshes:** **Read/Write** off unless the CPU reads the mesh: code, a Mesh Collider, a Particle System's Shape module (or its Renderer without GPU instancing) or a Terrain detail. Turn it on for those yourself. Unity 6000.6.2f1 still handles them during the build, with a warning that future versions won't (verified with a build); its documentation already says the build fails. Treat that warning as an error. Mesh Collider meshes also get pre-baked collision: [export reference](../game-assets/references/export.md#unity-import-settings).
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
- Web builds: the official `unity:optimize-web` skill.
