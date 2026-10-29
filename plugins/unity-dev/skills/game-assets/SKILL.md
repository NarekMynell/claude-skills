---
name: game-assets
description: Creates game-ready 3D models and environments in Blender through the Blender MCP connector - asset planning and reuse, modular kits, clean geometry, automated mesh validation, multi-angle checks, UVs, textures and materials, LODs, colliders, characters, and export to Unity.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
argument-hint: "[model]"
---

# Game-ready 3D assets

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require. Blender's Python API changes between versions: check an operator or property in the connected Blender (`search_api_docs`, `get_python_api_docs`) before using it.

## Before modeling

1. **Connector.** Call the Blender MCP `get_objects_summary` tool. If it fails, ask the user to start Blender with the MCP connector enabled, and stop until it responds.
2. **Unity primitives** (cube, sphere, capsule, cylinder, plane, quad) are for blockouts and for shapes they match exactly. Model your own when the asset needs another pivot, bevels, trim-sheet UVs or fewer triangles: Unity's Plane is 10 m wide with 200 triangles.
3. **Style and budget.** Read the art style and the triangle budget for this asset type from `docs/art-direction.md`. If they are missing, agree them with the user and record them there. Unity counts more vertices than Blender, because it splits them at UV seams and hard edges.
4. **References.** Use the user's reference images or real-world dimensions. Real-world scale: 1 unit = 1 m.
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

- No duplicate or overlapping coplanar faces: they z-fight and waste data.
- No hidden internal faces, loose vertices or edges, zero-area faces. Merge by distance.
- Normals point outward consistently. Smooth or flat shading is set on purpose, sharp edges marked. Blender 4.1+ has no auto smooth property: use `shade_smooth_by_angle`, or `shade_auto_smooth`, which adds a modifier.
- Polygons go where they are seen, on the silhouette, not on flat areas.
- Inspect the scene before changing it; never modify objects destructively without the user's confirmation.

## Validate

Run [scripts/validate_mesh.py](scripts/validate_mesh.py) after every significant change and before export:

1. Read the script.
2. Call `execute_blender_code` with the settings prepended to its content, for example:
   ```python
   TARGETS = ["Crate"]
   TRIANGLE_BUDGET = 800
   ```
3. `result.passed` must be `true`. Fix every reported issue and run it again.

It reports duplicate vertices and faces, overlapping and back-to-back coplanar faces, non-manifold edges (more than two faces), loose geometry, zero-area faces and zero-length edges, inconsistent normals, missing or degenerate UVs, unapplied transforms and budget overruns. `info` adds triangle count, ngons, open (boundary) edges, material slots, dimensions and texel density spread. Open edges are normal on intentionally open meshes; anything else is a defect.

## Visual check

Run [scripts/render_views.py](scripts/render_views.py) the same way with `OUTPUT_DIR` (an absolute path) and `TARGETS`. It renders front, side, top and perspective PNGs with a temporary camera and restores the scene. It shows image textures, or the base color of materials without one; set `COLOR = "VERTEX"` for vertex colors. Look at every image. Compare it with the reference, fix, and render again until it matches.

## Scale, transforms, origin

- Transforms applied: scale 1, rotation 0.
- The origin is placed for the object's use: bottom center for placeable props, the hinge for doors, the grip for held items, a module corner for kit pieces.
- Model the front facing Blender's −Y axis (toward the Front view).

## UVs

- No overlaps unless intentional (mirrored or tiling parts).
- Uniform texel density: each face's UV area is proportional to its surface area, and assets of the same kind share one density, recorded in pixels per meter. A high `texel_density_spread` points to stretched or uneven islands.
- Padding between islands in pixels, enough to survive the mipmaps the asset is seen at: a common baseline is 4 px at 1024² and 8 px at 2048². Blender's `uv.pack_islands` margin isn't in pixels by default: use `margin_method="FRACTION"` with `margin` = pixels ÷ texture size.
- Seams where they are least visible.
- Lightmap UVs for static meshes in baked lighting: a second UV set, inside 0–1, no overlaps, wide margins, low distortion, or Unity's **Generate Lightmap UVs**.

## Textures and materials

- **Blender's shader nodes don't reach Unity.** Unity receives the mesh, its UVs, vertex colors, material slot names and textures. Bake procedural or layered looks into textures on the asset's UVs before export, and build the materials in Unity with the URP shaders.
- **Shared textures over unique ones:** a trim sheet for architecture, an atlas for props, and for flat-colored stylized art a small palette texture that many props share with one material.
- **As few materials per mesh as possible:** each material is a separate draw.
- **PBR maps for URP Lit:** metallic in R and smoothness in A of the metallic map, occlusion in G (one channel-packed texture can fill both slots). Smoothness is 1 − Blender's roughness. Data textures have sRGB off; normal maps are imported as Normal Map. Triangulate before baking normal maps and export that same triangulation.
- Power-of-two texture sizes, chosen for the asset's on-screen size on the target devices.

## LODs and colliders

- **LODs** for objects seen at a distance. Authored levels use `_LOD0`, `_LOD1`, … suffixes (up to 8), which Unity's importer groups into a LOD Group; use them when the levels differ in materials or renderer settings. For geometry-only reduction, Unity's Mesh LOD generation on import (recent Unity 6 versions) uses less memory; it isn't for models that already have `_LODn` meshes.
- **Colliders:** primitive colliders (box, sphere, capsule, or a compound of them) first. A Mesh Collider only for static geometry, or convex (at most 255 triangles) on a moving object. A detailed render mesh gets a simplified collision mesh; a static piece whose render mesh is already simple may collide with it. A mesh used by a Mesh Collider needs **Read/Write** on, which is set per model file, so a separate collision mesh goes in its own file.

## Characters and animation

- One Skinned Mesh Renderer per character, at most 4 bone influences per vertex, and only the bones the animation needs: every bone costs animation time.
- Rigs import with **Optimize Game Objects**, so Unity doesn't create a GameObject per bone.
- Bake IK and constraints into the keyframes on export.
- Shape keys (blend shapes) export only without **Apply Modifiers**; keep smoothing exported (`mesh_smooth_type="FACE"`).
- The export settings differ from static meshes: see [references/export.md](references/export.md#rigged-and-animated-assets).

## Export and import

Exact exporter settings and the Unity import checklist: [references/export.md](references/export.md).

- FBX for authored assets; glTF (glTFast in Unity) for models loaded at runtime.
- After import, check the asset in Unity: rotation 0, scale 1, facing +Z, correct size next to a 1 m reference. Capture it from several angles through the Unity CLI and inspect the images.
