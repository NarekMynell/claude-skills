---
name: performance
description: Unity performance standards and optimization - budgets, frame rate per platform, CPU, GPU, memory and build size, draw and SetPass calls, batching, sprite atlases, textures, LODs, profiling on device.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# Unity performance

**Principle.** Design for performance from the start: architecture, data layout, pooling, no allocations in per-frame code (those code rules are in the [code standards](../code-standards/SKILL.md)). Micro-optimize only from profiler data captured on the target device, and measure every optimization before and after.

## Budgets

The project records its budgets in `docs/performance-budgets.md`:

- target devices, including the minimum-spec device;
- frame time (16.6 ms at 60 fps);
- memory, draw call and SetPass call budgets;
- build and download size.

Create the file when the target platforms are known. Check every milestone against it.

## Frame rate

Set it explicitly at startup (the library's Bootstrap module has a frame-rate step):

- **Android and iOS.** With the defaults (`vSyncCount = 0`, `targetFrameRate = -1`) Unity renders at a fixed 30 fps: the usual reason an optimized mobile game runs at 30. Set `QualitySettings.vSyncCount = 0` and `Application.targetFrameRate = 60`, or the display's refresh rate for games designed for high-refresh screens. On Android, enable **Optimized Frame Pacing**.
- **Web.** Use `QualitySettings.vSyncCount = 1`, not `targetFrameRate`: on Web, `targetFrameRate` uses software timing and micro-stutters.
- **Desktop.** vSync on, or a target equal to the display's refresh rate.

Mobile games hold at least 60 fps on the minimum-spec device, sustained: run 10+ minutes to see thermal throttling.

## CPU

- Event-driven by default. Per-frame work runs in `ITickable` systems; non-critical logic runs every N frames; heavy work is spread across frames or moved to Burst jobs.
- Profile before guessing. The usual hotspots: per-frame allocations (GC spikes), `Update` methods on many objects, physics queries without layer masks, UI layout rebuilds, `Instantiate` / `Destroy` during gameplay, synchronous loading.
- Expensive custom code is wrapped in a `ProfilerMarker` so it shows up by name in the Profiler.

## Rendering

- **Fewer draw calls and SetPass calls:** share materials and shaders; keep shaders SRP Batcher compatible; static batching for static scenery; the GPU Resident Drawer (Unity 6 URP, Forward+ path) or GPU instancing for many repeated meshes.
- **Shaders** are as simple as the look allows. Strip unused variants.
- **Effects, cheapest first:** a shader on the object's material → a renderer feature written for Render Graph → full-screen post-processing. Choose the cheapest that achieves the look.
- **Mobile:** control overdraw (transparent layers, particles, full-screen passes); bake lighting; few realtime lights and shadows; minimal post-processing.
- LODs for 3D objects seen at a distance. Occlusion culling in enclosed scenes.

## Memory

- Textures: size and compression set per platform (ASTC on mobile), mipmaps on 3D textures, none on UI.
- Meshes: Read/Write off unless code reads the mesh; compression set per quality need.
- Audio import settings: the official `unity:optimize-audio` skill.
- Every Addressables load has a matching release. Check for leaks with Memory Profiler snapshots taken before and after a level.

## Sprite atlases

- One sprite from an atlas keeps the **whole atlas texture** in memory.
- Group sprites by what is on screen together: a screen, a level, a character. Shared UI goes in one common atlas. Never pack unrelated content into one big atlas.
- With Addressables, an atlas and its sprites go in the same group; otherwise the texture is duplicated across bundles.
- Master and variant atlases and prebuild packing: the official `unity:manage-sprite-atlas` skill.

## Profiling

- Profile a **development build on the target device**, not the Editor. Editor numbers include Editor overhead and a different GPU.
- Tools: Profiler (CPU, GPU, memory), Frame Debugger (draw calls, SetPass calls, batching breaks), Memory Profiler (snapshots, leaks), Profile Analyzer (before/after comparison).
- Record the result of each optimization (metric before, after, device) in the change description.

## Build size

- Managed code stripping as high as the project tolerates. Code that relies on reflection is protected with `link.xml`.
- Remove unused packages and assets. Read the build report after every release build.
- Web builds: the official `unity:optimize-web` skill.
