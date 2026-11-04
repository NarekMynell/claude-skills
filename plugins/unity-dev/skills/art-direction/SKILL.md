---
name: art-direction
description: Gives a game a current, beautiful look - references, palette and value plan, shape language, stylized light with no runtime cost, environment composition from the game camera, readable scale on a phone, one final-quality screen before production, screenshot studies against references.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# Art direction

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

How a game's look is chosen, built and judged. The models come from [game assets](../game-assets/SKILL.md) and [characters](../characters/SKILL.md), the cost of each technique from [performance](../performance/SKILL.md).

## Must

- **The look is chosen before anything is produced,** from references, and written in `docs/art-direction.md`: references, palette, value plan, shape language, light, what the camera sees. Every asset follows it.
- **One screen at final quality before mass production:** a real scene of the game, from its real camera, on the target device or at its resolution, that passes the review below. Everything else follows it. A first version of everything, polished later, is the way to throw it all away.
- **Judged in the running game,** from the game's camera, at phone size, never only in review renders. Grayscale reads; the eye knows where to go.
- **Current, not dated:** no flat fills, no default colors, no visible facets on curves, no empty ground. Beautiful and cheap together: the techniques below cost almost nothing at runtime.
- **The proof:** [study_screenshot.py](../game-assets/scripts/study_screenshot.py) on real game screenshots with the references, `PROOF_DIR` set to `docs/proofs`. Every gap it reports (`issues`) is closed, or the user accepts it; each of its `notes` is answered in writing. A written critique names the three things the references do best that the game doesn't; fix those, and repeat until the [fresh review](../standards/references/fresh-review.md) can't name three. Without references, this must stays unproven, and the report says so.

The techniques below are a guide: which look fits this game, and how to reach it, is your decision.

## What has failed

A real project, rejected by its owner as primitive and dated, twice. Measured on its screenshots with `study_screenshot.py`: 94% of the picture in the top two of five value bands, its darkest 5% still at value 0.58, two hue families, shadows no cooler than its lights.

- Flat, saturated green next to flat sand, with hard edges between them.
- "Round" enclosures with visible polygon corners.
- Large empty ground; blobby trees of the same size; nothing dark for the eye to rest against.
- Reviews done on hero renders, which looked fine, instead of on the game's own camera.

## References

Collect 5 to 10 screenshots of current top games in the genre and of the look you want, plus art outside games if it helps. Sources: store pages, [Game UI Database](https://www.gameuidatabase.com), reference posts on 80.lv. Through the browser tools a page can be captured for study; an image the browser can't reach is the user's to supply. References stay out of the project's shipped assets and out of git.

For each, write what makes it work: where its darks are, how many colors carry it, how shadows are colored, how ground breaks up, how big characters are on screen. Run `study_screenshot.py` on them: their numbers become your targets. Ask the user for references at the start, when you can't reach any. Without any image, work from written sources, and report the look as unproven: `study_screenshot.py` itself reports `no_references`.

## Shape

- **Stylized art reads through shape, palette and silhouette,** not surface detail. Exaggerate what is real: bigger highlights, bigger scratches, more saturation, chunkier forms.
- Rounded, chunky forms with soft bevels catch light; hard flat boxes and thin planks look old. One shape language per world: rounder for friendly, angular for dangerous.
- Every model has a silhouette that reads at game distance. Group detail into big, medium and small; most of it can go.
- **Curves stay curves.** Enough segments and smooth normals for the size on screen. A visible polygon corner on something round is the fastest way to look cheap.

## Color

- **Value first.** Plan the picture in gray, then add hue. Squint: if the grayscale doesn't read, no color will save it (James Gurney; the grayscale test in Game Developer's visual clarity article).
- **Keep darks.** Ground and background get lower contrast, heroes and things to act on get the brightest and highest contrast. Everything bright and contrasty at once is as confusing as everything dull.
- **Light and shadow differ in hue.** Warm light, cooler shadow, relative to each other, not literally blue. Shadows pick up reflected light from their neighbors. Darkening alone looks flat: change hue, saturation and value together when you step along a color.
- **A limited palette from a plan.** Choose a gamut on the color wheel (Gurney's gamut masking) and stay inside it. Premix about four values per color family. A dominant color family, a supporting one, and an accent kept for what matters. Picking it from your references is a good start.
- **Saturation is a hierarchy.** Points of interest get more of it; backgrounds less. A whole screen at full saturation has no focus and looks childish or cheap.
- **Inside a large color area, keep varying** hue and value. A flat 60% of anything is dead: `flat_share` in `study_screenshot.py` measures it.

## Light with no runtime cost

Everything here is baked or computed in a simple shader. Costs and setup: [performance](../performance/SKILL.md#light).

- **One dominant light,** saturated enough to feel like a moment of day, with an ambient that complements it: warm sun, blue-violet ambient.
- **A gradient on every surface:** darker and more saturated near the ground, lighter toward the top. Supercell's artists keep albedo to a couple of color variations and use simple value gradients to lead the eye.
- **Baked occlusion** in vertex colors or textures: dark where things meet the ground and each other. It grounds everything, and costs nothing.
- **Paint light from above,** since the player mostly sees from above, in one consistent direction.
- **A fake rim or edge highlight** from a fresnel term or edge-wear in the texture, in a simple shader.
- **Color grading** through a LUT is the most effect for the least work; on URP mobile it can run on-tile ([details](../performance/SKILL.md#light)). Keep textures fairly neutral, and let light and grading set the mood.

## Environment from the game's camera

Compose what the camera sees, not the object.

- **Choose the point of interest first,** then build outward. Put the most animated and detailed things there, and tall things behind it.
- **Break up the ground:** low-frequency color variation in world space, a second tile or tint blended by a noise mask, darker near objects. Paths and lawns meet in a soft, irregular edge with scattered detail across it, never a clean polygon line.
- **Density and rhythm.** Clusters and gaps instead of even spacing. Big, medium, small next to each other. Empty space is deliberate, framed by something.
- **Depth in layers,** each with its own value and color: foreground, play area, background. Fog or a gradient separates them cheaply.
- **Trees and rocks** clump into masses with rounded gradient shading, in a few shape variants of different sizes. A flat, even canopy reads flat.
- **Life.** Something moves in every view: leaves in the shader, water, a flag, birds, people.

## Scale on a phone

- Review at the real size of the screen. What can't be read at that size is removed or made bigger. Only silhouette and value survive small.
- Proportions exaggerate with distance: bigger heads, hands and props when the camera is far. Set the on-screen height of a person in pixels in `docs/art-direction.md`, and check characters with `GAME_PIXELS` in [render_views.py](../game-assets/scripts/render_views.py).
- Decide what the player must see at each zoom level, and build for it.

## Rich surfaces, cheap

Most of a stylized world can be a few textures and vertex colors. One Unity breakdown covered about 95% of its scene with 5 textures.

- **Vertex colors** with gradients and baked occlusion, for most of what is smooth; no texture sampling.
- **A palette or gradient texture:** UVs into a tiny strip of colors give many objects one material, and gradients instead of flat fills.
- **Grayscale tiled detail** tinted by vertex color, with vertex alpha blending a second texture for dirt and variation.
- **Trim sheets** for modular pieces with repeating detail.
- **World-space noise** for macro variation over mesh UVs; triplanar costs three samples per pixel, so profile it on a device first.

## The review

From a real screenshot of the game, at device size, with `study_screenshot.py` and references beside it. Write it, then fix it.

- **Gray and blur:** does the eye land where it should? Are there real darks and lights, in big clear shapes?
- **Palette:** does it hold, or did every asset bring its own colors? Are shadows colored?
- **Numbers against references:** value range, flat share, saturation, and the script's notes. A gap is a question to answer on purpose.
- **Surfaces:** anything flat? Anything faceted? Does every object sit on the ground, with occlusion under it?
- **Ground and space:** dead areas? Hard edges?
- **Dated?** Would a player scrolling a store page today stop here, next to the top games of the genre? Name what stops them, and what would.
- **Cost:** what does this look spend on the phone? Anything that doesn't show can go.

## Sources

[Supercell Helsinki on Clash's look](https://www.adobe.com/products/substance3d/magazine/supercell-helsinki-creating-stylized-content-for-clash-of-clans-and-clash-royale.html), [80.lv on stylized production](https://80.lv/articles/advice-for-stylized-3d-art-production), [80.lv on environment design](https://80.lv/articles/the-strings-of-environment-design/), [80.lv on a Unity stylized environment](https://80.lv/articles/stylized-environment-production-in-unity), [reducing visual confusion](https://www.gamedeveloper.com/design/how-to-reduce-visual-confusion-in-your-game), [Gurney on gamut masking](https://gurneyjourney.blogspot.com/2011/09/part-1-gamut-masking-method.html), [Gurney on warm and cool light](https://gurneyjourney.blogspot.com/2008/01/golden-hour.html), [Meta's art preproduction pipeline](https://developers.meta.com/horizon/design/art-preproduction/). No studio publishes numbers for mobile art direction: the numbers in this guide come from measuring, and your targets from your references.
