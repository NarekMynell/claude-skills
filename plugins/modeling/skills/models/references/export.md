# Export

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require. Check every exporter option in the connected Blender before use; they change between versions.

[export_fbx.py](../../../scripts/export_fbx.py) exports an asset only after its checks pass: export through it rather than calling the exporter yourself. Axes, scale, transforms and every other exporter option are the engine's: the script's defaults are the ones Unity needs (`unity-dev:models` lists them and what they give there), and `FBX` lays another engine's options over them, from that engine's guide. For an engine without a guide, export one test asset first, check its rotation, scale, facing and animation there, and record the options that work in `docs/art-direction.md`.

## Any asset

- One asset per file, named after the asset (`Crate.fbx`). LODs use `_LOD0`, `_LOD1`, … suffixes.
- Export into the engine project's art folder only when the user asked to; otherwise export next to the `.blend` file.
- **Instances.** Linked duplicates and collection instances export as one shared mesh, but only while no live modifier is applied on export and **Triangulate Faces** is off: apply modifiers and triangulation to the source mesh first. Export layouts as empties named after their assets, and replace them with instances of those assets in the engine.
- Textures are imported on their own, never embedded; vertex colors leave as Blender renders them.

## Rigged and animated assets

- **Apply Transform** (`bake_space_transform`) is documented by Blender as broken with armatures and animations: rigs never use it, so the axis conversion lands on the objects under the root instead of in the vertices. That is correct; never zero those rotations.
- **Deform bones only** (`use_armature_deform_only`), no leaf bones. The exporter writes a non-deforming bone anyway when a deform bone is its child: every deform bone's parent must deform too (Rigify's `DEF` bones hang under `ORG` bones, so a Rigify rig doesn't export clean).
- **Baked, unreduced keys:** IK and constraints baked into keyframes, no key reduction (reduced keys move planted feet and hands), the current action only, one clip per file (`Character@Walk.fbx`).
- **Frame range.** The exporter bakes the scene's frame range, not the action's: set the scene's start and end to the action's range first (`export_fbx.py` does, and restores them).
- **Modifiers and shape keys.** Armature modifiers are never applied on export. Other modifiers, such as Mirror, are applied with `use_mesh_modifiers=True`, which drops shape keys. A mesh with shape keys exports with `False`, so apply its other modifiers to the source first.
- For a rig with IK, constraints or unusual bone rolls, or after a Blender or engine upgrade, export one test asset first and check it in the engine.

## glTF (runtime loading)

```python
bpy.ops.export_scene.gltf(
    filepath="/abs/path/Crate.glb",
    export_format="GLB",
    use_selection=True,
    export_apply=True,                # apply modifiers; prevents exporting shape keys
    export_yup=True,
)
```

Keep textures power-of-two. Blender writes PNG, JPEG or WebP only: GPU-compressed textures need KTX2 (`KHR_texture_basisu`) made with an external tool, and Draco mesh compression needs the engine's Draco support. The loader is the engine's (Unity: `unity-dev:models`).
