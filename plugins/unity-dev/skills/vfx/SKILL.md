---
name: vfx
description: Visual effects for Unity games - effect design and timing, no hard edges or visible masking, Particle System vs VFX Graph vs Shader Graph vs post-processing, overdraw, pooling, checks at gameplay speed.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# VFX

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

## Design

- **Purpose first.** Gameplay readability beats spectacle.
- **Timing in three beats:** anticipation, impact, dissipation.
- **Layers:** core, glow, sparks or debris, smoke, distortion.
- **Colors** come from the art direction (`docs/art-direction.md`).
- **Creativity.** Go beyond the obvious first idea. Every effect has its own identity and stays consistent with the game's style.

## No hard edges

- Textures fade to zero alpha before their borders.
- Effects fade out instead of popping.
- No mask or clipping cuts an effect into a visible rectangle.
- Culling bounds cover the whole effect.
- Sorting is correct against the scene and the UI.

## Which tool

- **Particle System:** the default. Runs everywhere, including mobile and Web.
- **VFX Graph:** very large particle counts, only on platforms with compute shaders and no OpenGL ES, so not on WebGL or OpenGL ES Android devices. Its URP support is still in preview: check the VFX Graph system requirements for the project's version before relying on it for a mobile or Web target.
- **Shader Graph:** surface effects such as dissolve, glow, hologram, distortion.
- **Post-processing** (bloom and similar) is used deliberately, with its mobile cost in mind; setup in the official `unity:urp-postprocessing` skill.

## Performance

- Overdraw is the main cost: limit large transparent particles and stacked layers.
- Small texture sheets, shared materials.
- Effects are pooled (library Pooling module). On mobile, effects don't create realtime lights.

## Verify

At gameplay speed and slowed down, from the gameplay camera, on the target device. Capture frames through the Unity CLI and inspect them before reporting.
