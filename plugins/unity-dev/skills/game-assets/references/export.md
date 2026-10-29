# Export and import

## FBX (authored assets)

Select the objects to export, then run through `execute_blender_code`:

```python
import bpy

bpy.ops.export_scene.fbx(
    filepath="/abs/path/Crate.fbx",
    use_selection=True,
    object_types={"MESH"},            # add "ARMATURE" for rigs, "EMPTY" for hierarchies
    apply_scale_options="FBX_SCALE_ALL",
    apply_unit_scale=True,
    axis_forward="-Z",
    axis_up="Y",
    bake_space_transform=True,        # "Apply Transform"
    use_mesh_modifiers=True,
    mesh_smooth_type="FACE",
    add_leaf_bones=False,
    bake_anim=False,                  # True for animated assets
    path_mode="STRIP",                # textures are imported separately
)
```

These settings are a starting point verified against Blender 5.2's exporter. The real criterion is the result in Unity: rotation 0, scale 1, facing +Z. If an asset imports rotated, fix the export settings, not the instance in the scene.

- One asset per file, named after the asset (`Crate.fbx`). LODs use `_LOD0`, `_LOD1`, … suffixes.
- Export into the Unity project's art folder (`Assets/_Project/Art/...`) only when the user asked to; otherwise export next to the `.blend` file.

## glTF (runtime loading)

```python
bpy.ops.export_scene.gltf(
    filepath="/abs/path/Crate.glb",
    export_format="GLB",
    use_selection=True,
    export_apply=True,                # apply modifiers
    export_yup=True,
)
```

Load it in Unity with glTFast. Keep textures power-of-two and compressed for the target platform.

## Unity import settings

Set them in the model's import settings, or with an `AssetPostprocessor` when every asset of a folder shares them:

- **Read/Write** off unless code reads the mesh.
- **Mesh Compression** per quality need: higher compression for distant or small props.
- **Import Cameras** and **Import Lights** off.
- **Materials:** don't use the embedded materials. Assign or remap to the project's materials.
- **Animation Type** None for static meshes; **Import Animation** off.
- **Generate Colliders** off: colliders come from primitives or a dedicated collision mesh.
- **Generate Lightmap UVs** on for static meshes in baked lighting without their own second UV set.

## Check in Unity

Place the asset next to a 1 m reference cube, check its transform (rotation 0, scale 1) and facing (+Z), and capture the scene from several angles through the Unity CLI. Inspect every image before reporting.
