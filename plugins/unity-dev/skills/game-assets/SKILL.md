---
name: game-assets
description: Creates game-ready 3D models and environments in Blender through the Blender MCP connector - asset planning and reuse, modular kits, clean geometry, automated checks, contact-sheet reviews, UVs, textures and materials, LODs, colliders, and export to Unity.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
argument-hint: "[model]"
---

# Game-ready 3D assets

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require. Blender's Python API changes between versions: check an operator or property in the connected Blender (`search_api_docs`, `get_python_api_docs`) before using it.

Characters follow the [characters](../characters/SKILL.md) guide, and their motion the [animation](../animation/SKILL.md) guide. Both build on this one.

## How to work

- **Build with code, judge with checks and renders.** Create and edit geometry with `bpy` and `bmesh` through `execute_blender_code`: exact, repeatable, cheap to redo. Never model by clicking through the UI from screenshots: vision judges the result, it doesn't build it.
- **Code builds what code describes well:** hard-surface props, architecture, modular kits, stylized low-poly shapes. It doesn't sculpt organic forms: a body, face, hand or animal made of primitives or moved vertices looks wrong however long it's tweaked. Those start from a professional base, as the characters guide describes.
- **Small steps, each verified:** blockout, form, detail, UVs, materials, export. Check after each step and fix before the next; a defect found late costs a rebuild.
- **The review loop**, after every significant change:
  1. **Checks.** [validate_mesh.py](scripts/validate_mesh.py), plus the character or animation checks for those assets. Numbers catch what eyes miss: stacked faces, bad weights, penetration. Fix until `passed` is true.
  2. **Contact sheet.** [render_views.py](scripts/render_views.py) renders every side and the close-ups into one image. Look at every tile.
  3. **Written critique** against the [review checklist](references/review.md) and the references: list every defect with its tile, its cause and its fix before fixing anything. "Looks good" isn't a review; name what each tile shows.
  4. **Fix all of them, then go back to 1.** Done means a clean check and a clean critique in the same round.
- **Change the approach, not the patch.** When a defect survives two rounds of fixes, the construction is wrong: rebuild that part another way, with a different base, topology or method.
- **Honest reports:** what the checks and sheets show, including what's left. An asset with a known defect isn't done.

**Tokens.** Quality first, then cost. Scripts run by path, so their code never enters the conversation. Numbers come before pictures: a check costs a few hundred tokens, a sheet about 1,200 (6 tiles of 384 px) to 2,400 (12 tiles). One sheet per review round instead of a screenshot per angle; close-ups only where a check or the sheet points. Never screenshot the Blender window for a review: its UI wastes most of the image. Fix every listed defect, then check once.

## Running the scripts

The scripts are in [scripts/](scripts/), next to this file. Run them by path through `execute_blender_code`, with their settings in the namespace:

```python
P = "/absolute/path/to/game-assets/scripts/validate_mesh.py"
ns = {"__file__": P, "TARGETS": ["Crate"], "TRIANGLE_BUDGET": 800}
exec(compile(open(P).read(), P, "exec"), ns)
result = ns["result"]
```

`P` is the script's absolute path: the folder you read this guide from, then `scripts/`, with `~` expanded. Each script's docstring, its first lines, lists the settings; don't read the rest. They leave the scene as they found it. If the connector's Blender runs on another machine and can't open the path, send the script's content instead.

| Script | Does | When |
|---|---|---|
| validate_mesh.py | Duplicate, overlapping and z-fighting faces, also between objects; non-manifold edges, loose geometry, normals, UVs, transforms, triangle budget, triangles wasted on flat areas. `examples` give each problem's position | After every geometry change, and before export |
| render_views.py | One contact sheet: all sides, 3/4 views, close-ups, wireframe, proportion grid, floor, animation frames | Every review round |
| inspect_character.py | Anatomy, covered and intersecting surfaces, rig, weights, deformation in test poses | [Characters](../characters/SKILL.md) |
| inspect_animation.py | Foot contact and sliding, in-place speed, arm swing, loops, pops, limbs through the body or props | [Animation](../animation/SKILL.md) |
| export_fbx.py | Runs the checks, refuses a failing asset, exports with the Unity settings | Export |

## Before modeling

1. **Connector.** Call the Blender MCP `get_objects_summary` tool. If it fails, ask the user to start Blender with the MCP connector enabled, and stop until it responds.
2. **Unity primitives** (cube, sphere, capsule, cylinder, plane, quad) are for blockouts and for shapes they match exactly. Model your own when the asset needs another pivot, bevels, trim-sheet UVs or fewer triangles: Unity's Plane is 10 m wide with 200 triangles.
3. **Style and budget.** Read the art style and the triangle budget for this asset type from `docs/art-direction.md`. If they are missing, agree them with the user and record them there. Unity counts more vertices than Blender, because it splits them at UV seams and hard edges.
4. **References.** The user's reference images, or real-world dimensions. Real-world scale: 1 unit = 1 m.
5. **Plan the set** before modeling anything for a scene or a game: list the unique assets, how many times each appears, and which share a kit, a material or a texture. Record the list in `docs/art-direction.md`.

## Reuse, don't duplicate

Objects that differ only in position, rotation, scale or color are one asset placed many times. Never model them as separate meshes, and never merge them into one mesh: a merged mesh is culled, lit and LODed as one object, can't be instanced, and stores every copy's vertices. The [performance guide](../performance/SKILL.md#repeated-objects) has the Unity side.

- **One asset, many instances.** Model each unique asset once, export it once, and make it one prefab in Unity. A scene is built from prefab instances, placed in Unity, where Claude can place them through the Unity CLI.
- **Layouts drafted in Blender** place copies as linked duplicates (`Alt+D`) or collection instances, never as full copies. They travel to Unity as transforms: empties named after their asset, replaced by prefab instances in Unity. Blender's FBX exporter writes linked duplicates as one shared mesh, but only without live modifiers applied on export and without **Triangulate Faces**: apply both to the source mesh first.
- **Variation without new meshes:** rotation and scale per instance; color through Material Variants or a per-renderer value read by the shader; a vertex-color mask in the mesh for tinting parts. Never a material copy per object.
- **Enough variants to hide the repetition:** 3 to 5 shapes per common prop (rocks, trees, crates), each placed many times with rotation and scale jitter. One shape repeated everywhere looks generated.
- **Merge only what is one object:** static parts that never move relative to each other and are always seen together, such as the planks of one crate. Never a whole environment or level.

## Modular kits

- **One grid per project**, recorded in `docs/art-direction.md`: a module size (such as 1 m, 2 m or 4 m), with every piece a whole number of modules.
- Vertices that meet a neighbor sit exactly on the grid. Pivots sit on a module corner or edge, so pieces snap with Unity's grid snapping.
- Pieces share one texel density and one trim sheet or atlas, so seams between them match.
- Corners, ends and transitions exist as pieces of their own, so the kit closes every shape without overlaps.

## Geometry: every vertex has a purpose

- **No stacked faces**, within an object or between objects. Faces facing the same way closer than `ZFIGHT_DISTANCE` (2 mm by default) z-fight. Depth precision is worst on WebGL and mobile GLES, which don't use reversed depth: with a 0.3 m near plane, a 24-bit depth buffer resolves about 0.5 mm at 50 m and 2 mm at 100 m. Delete the hidden face, or keep a larger gap for distant views. Common causes:
  - an extrude cancelled without moving, which leaves a copy of the faces;
  - touching primitives joined into one mesh;
  - a Mirror modifier without Merge or Clipping, or Solidify on a closed mesh;
  - boolean leftovers;
  - a second copy of an object in the same place;
  - a decal laid flat on a surface;
  - LOD or collision meshes left visible.

  Check the whole asset at once, every part in `TARGETS`: faces in separate objects z-fight too. Opposite-facing touching faces, such as a box on a floor or a thin sheet, appear in `info`: they don't z-fight with back faces culled, only with two-sided materials.
- **No hidden faces:** inside other geometry, or under parts that always cover them, such as the bottom of a prop fixed to the floor or a body under clothes.
- No loose vertices or edges, no zero-area faces, no duplicate vertices: merge by distance.
- Normals point outward consistently. Smooth or flat shading is set on purpose, with sharp edges marked. Blender 4.1+ has no auto smooth property: use `shade_smooth_by_angle`, or `shade_auto_smooth`, which adds a modifier.
- **Polygons where they show:** on the silhouette, where it deforms and where light changes, never on flat areas. `flat_area_extra_triangles` counts the triangles perfectly flat areas don't need. Set `FLAT_DETAIL` only when they do something: the area deforms (cloth, flags) or carries vertex-color detail.
- **No noise as detail.** Random vertex jitter, noise displacement and noise textures read as damage, and they break the shading. Detail comes from deliberate shapes, bevels and textures; every bump has a reason the art direction names.
- **Planar faces** on hard surfaces: a quad or n-gon bent out of its plane shades differently with each triangulation. Split it on purpose where it bends.
- Inspect the scene before changing it; never modify objects destructively without the user's confirmation.

## Scale, transforms, origin

- Transforms applied: scale 1, rotation 0.
- The origin is placed for the object's use: bottom center for placeable props, the hinge for doors, the grip for held items, a module corner for kit pieces.
- Model the front facing Blender's −Y axis (toward the Front view).

## UVs

- No overlaps unless intentional (mirrored or tiling parts).
- Uniform texel density: each face's UV area is proportional to its surface area, and assets of the same kind share one density, recorded in pixels per meter. A high `texel_density_spread` points to stretched or uneven islands; a checker texture on the model shows where.
- **Padding between islands** in pixels, sized for the smallest mip the asset is seen at. Each mip level halves the gap, so a gap of p px lasts about log2(p) levels: 4 px at 1024² and 8 px at 2048² both last until the 256² mip, the same on-screen size. An asset seen smaller needs a wider gap. Blender's `uv.pack_islands` margin isn't in pixels by default: use `margin_method="FRACTION"` with `margin` = pixels ÷ texture size.
- **Bake with a margin** at least as wide as the padding (`scene.render.bake.margin`, in pixels, default 16). It extends each island's edge colors into the gap, so a lower mip blends an island with its own colors, not with its neighbor's.
- Seams where they are least visible.
- Lightmap UVs for static meshes in baked lighting: a second UV set, inside 0–1, no overlaps, wide margins, low distortion, or Unity's **Generate Lightmap UVs**.

## Textures and materials

- **Blender's shader nodes don't reach Unity.** Unity receives the mesh, its UVs, vertex colors, material slot names and textures. Bake procedural or layered looks into textures on the asset's UVs before export, and build the materials in Unity with the URP shaders.
- **Shared textures over unique ones:** a trim sheet for architecture, an atlas for props, and for flat-colored stylized art a small palette texture that many props share with one material.
- **As few materials per mesh as possible:** each material is a separate draw.
- **No artifacts in textures.** Every mark is intended: no noise, smears, blotches or visible seams. Base color holds color only, without baked lighting, shadows or highlights; AI-generated textures usually carry them, so remove them or don't use the texture. Look at each texture on the model in a close-up tile, at full resolution.
- **Bakes:** triangulate before baking normal maps and export that same triangulation; enough samples (a noisy bake had too few); a cage or ray distance that covers the high-poly without catching neighboring parts; base color baked from color alone, with no lighting.
- **PBR maps for URP Lit:** metallic in R and smoothness in A of the metallic map, occlusion in G (one channel-packed texture can fill both slots). Smoothness is 1 − Blender's roughness. Data textures have sRGB off; normal maps are imported as Normal Map.
- Power-of-two texture sizes, chosen for the asset's on-screen size on the target devices.
- **Sources:** made on purpose for the asset, the project's own, or CC0 libraries: ambientCG (CC0, no credit needed) and Poly Haven (CC0; its API asks for a visible credit and a unique User-Agent). Record every third-party asset in `docs/third-party-assets.md`: source URL, author, license, date obtained.

## LODs and colliders

- **LODs** for objects seen at a distance. Authored levels use `_LOD0`, `_LOD1`, … suffixes (up to 8), which Unity's importer groups into a LOD Group; use them when the levels differ in materials or renderer settings. For geometry-only reduction, Unity's Mesh LOD generation on import (recent Unity 6 versions) uses less memory; it isn't for models that already have `_LODn` meshes.
- **Colliders:** primitive colliders (box, sphere, capsule, or a compound of them) first. A Mesh Collider only for static geometry, or convex (at most 255 triangles) on a moving object. A detailed render mesh gets a simplified collision mesh; a static piece whose render mesh is already simple may collide with it. A mesh used by a Mesh Collider needs **Read/Write** and pre-baked collision on ([export reference](references/export.md#unity-import-settings)). Both are set per model file, so a separate collision mesh goes in its own file. List collision meshes in `ZFIGHT_IGNORE` when they share a scene with the render mesh.

## Export and import

[export_fbx.py](scripts/export_fbx.py) runs the checks and exports only an asset that passes, with the settings in [references/export.md](references/export.md). `FORCE` exports anyway, only after the user has accepted each listed issue.

- FBX for authored assets; glTF (glTFast in Unity) for models loaded at runtime.
- After import, check the asset in Unity: rotation 0 and scale 1 on the model root, facing +Z, correct size next to a 1 m reference. Capture it from several angles through the Unity CLI and inspect the images.
