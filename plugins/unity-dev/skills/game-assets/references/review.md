# Visual review

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

How to critique a contact sheet from `render_views.py`, and what to look for in props and environments. Characters add their own list: [character review](../../characters/references/review.md). Vision models miss small spatial defects that numbers catch, and numbers miss how a shape reads: run the checks first, then review.

## Method

1. **One tile at a time.** Name what it shows and compare it with the reference and with the real object. A tile you can't judge needs a close-up (`CLOSEUPS`) or another render, not a guess.
2. **The right render for the question:**
   - `COLOR="TEXTURE"` (default): the asset as the game shows it;
   - `LIGHT="MATCAP"` with `COLOR="SINGLE"`: the surface alone, where dents, bumps, faceting and shading errors stand out;
   - `WIREFRAME=True`: topology and density;
   - `COLOR="OBJECT"`: which part is which, for layered or multi-part assets;
   - `GRID=n`: proportions in equal parts of the height.
3. **Write the defect list** before fixing: tile, what is wrong, likely cause, fix. Mark each as fixed only after the next round's check and sheet show it fixed.
4. **Compare with professional work, not with the previous round.** A defect that has been there from the start is still a defect.

## Props and environments

- **Silhouette:** reads clearly at the distance the game shows it; no detail too small to see from there.
- **Proportions and scale:** match the reference and real dimensions, next to a 1 m reference: a door about 2.0–2.1 m high, a table top about 0.75 m, a chair seat about 0.45 m, a stair step 0.15–0.18 m high and 0.28–0.30 m deep. Parts have believable thickness: no paper-thin walls, planks or blades unless the style asks for them.
- **Construction:** parts that should touch, touch; nothing floats; nothing pokes through another part where it shows. Hinges, joints and fasteners sit where they would work.
- **Surface (matcap):** no dents, bumps, spikes or creases the design doesn't name; smooth areas without facets; hard edges crisp; no dark streaks or smears from bent faces or wrong normals.
- **Topology (wireframe):** density follows curvature and the silhouette; flat areas use the fewest faces; no long thin triangles across visible surfaces; even quads where the surface bends.
- **Textures:** no stretching or swimming (checker), seams hidden, one texel density across the asset and its kit, no noise or blotches, no lighting in the base color, colors from the art direction's palette.
- **Orientation:** front toward −Y, origin where the guide puts it for the object's use, sitting on the floor line when it stands on the ground.
- **Kit pieces:** pieces meet exactly on the grid with no gaps, overlaps or seams where they join.
