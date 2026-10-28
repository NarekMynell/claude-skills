---
name: vfx
description: Visual effects for Unity games. Covers effect design (purpose, anticipation-impact-dissipation timing, layers, palette), no hard edges or visible masking, choosing Particle System vs VFX Graph vs Shader Graph vs post-processing per platform, overdraw and pooling, and verification at gameplay speed. Use when creating or improving particles, hit effects, explosions, trails, magic, dissolves, glows or any other visual effect.
---

# VFX

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
- **VFX Graph:** very large particle counts, only on platforms with compute shader support. That excludes WebGL.
- **Shader Graph:** surface effects such as dissolve, glow, hologram, distortion.
- **Post-processing** (bloom and similar) is used deliberately, with its mobile cost in mind; setup in the official `unity:urp-postprocessing` skill.

## Performance

- Overdraw is the main cost: limit large transparent particles and stacked layers.
- Small texture sheets, shared materials.
- Effects are pooled (library Pooling module). On mobile, effects don't create realtime lights.

## Verify

At gameplay speed and slowed down, from the gameplay camera, on the target device. Capture frames through the Unity CLI and inspect them before reporting.
