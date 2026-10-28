---
name: game-assets
description: Creates game-ready 3D models in Blender through the Blender MCP connector and exports them to Unity or another engine. Covers art style and polygon budget, clean geometry (no duplicate or overlapping faces, no non-manifold edges, consistent normals), automated mesh validation, multi-angle visual checks, scale and origin, UVs and texel density, materials, LODs, colliders, FBX/glTF export and Unity import settings. Use whenever a 3D model, prop, character or environment piece is needed for a game.
---

# Game-ready 3D assets

## Before modeling

1. **Connector.** Call the Blender MCP `get_objects_summary` tool. If it fails, ask the user to start Blender with the MCP connector enabled, and stop until it responds.
2. **Never model a Unity primitive** (cube, sphere, capsule, cylinder, plane, quad): use the engine's.
3. **Style and budget.** Read the art style and the polygon budget for this asset type from `docs/art-direction.md`. If they are missing, agree them with the user and record them there.
4. **References.** Use the user's reference images or real-world dimensions. Real-world scale: 1 unit = 1 m.

## Geometry: every vertex has a purpose

- No duplicate or overlapping coplanar faces: they z-fight and waste data.
- No hidden internal faces, loose vertices or edges, zero-area faces. Merge by distance.
- Normals point outward consistently. Smooth or flat shading is set on purpose, sharp edges marked.
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

Run [scripts/render_views.py](scripts/render_views.py) the same way with `OUTPUT_DIR` (an absolute path) and `TARGETS`. It renders front, side, top and perspective PNGs with a temporary camera and restores the scene. Look at every image. Compare it with the reference, fix, and render again until it matches.

## Scale, transforms, origin

- Transforms applied: scale 1, rotation 0.
- The origin is placed for the object's use: bottom center for placeable props, the hinge for doors, the grip for held items.
- Model the front facing Blender's −Y axis (toward the Front view).

## UVs

- No overlaps unless intentional (mirrored or tiling parts).
- Uniform texel density: each face's UV area is proportional to its surface area, and assets of the same kind share one density. A high `texel_density_spread` points to stretched or uneven islands.
- Padding between islands: at least 4 px at 1024², 8 px at 2048².
- Seams where they are least visible.
- A second UV set for lightmaps when lighting is baked, or Unity's **Generate Lightmap UVs**.

## Materials

- As few per mesh as possible: each material is an extra draw call.
- Share texture atlases and trim sheets across props.
- PBR maps; normal maps set to Non-Color. Triangulate before baking normal maps and export that same triangulation.

## LODs and colliders

- Objects seen at a distance get LODs (`_LOD0`, `_LOD1`, … suffixes, which Unity's importer groups automatically).
- Collision uses primitives or a separate low-poly mesh, never the render mesh.

## Export and import

Exact exporter settings and the Unity import checklist: [references/export.md](references/export.md).

- FBX for authored assets; glTF (glTFast in Unity) for models loaded at runtime.
- After import, check the asset in Unity: rotation 0, scale 1, facing +Z, correct size next to a 1 m reference. Capture it from several angles through the Unity CLI and inspect the images.
