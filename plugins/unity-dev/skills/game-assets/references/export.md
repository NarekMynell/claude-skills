# Export and import

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require. Check every exporter option in the connected Blender before use; they change between versions.

## FBX: static meshes

Select the objects to export, then run through `execute_blender_code`:

```python
import bpy

bpy.ops.export_scene.fbx(
    filepath="/abs/path/Crate.fbx",
    use_selection=True,
    object_types={"MESH"},            # add "EMPTY" for hierarchies and layout markers
    apply_scale_options="FBX_SCALE_ALL",
    apply_unit_scale=True,
    axis_forward="-Z",
    axis_up="Y",
    bake_space_transform=True,        # "Apply Transform": experimental, and broken with armatures
    use_mesh_modifiers=True,          # False for meshes with shape keys
    mesh_smooth_type="FACE",
    colors_type="LINEAR",             # vertex colors arrive in Unity as Blender rendered them
    add_leaf_bones=False,
    bake_anim=False,
    path_mode="STRIP",                # textures are imported separately
)
```

Verified against Blender 5.2 and Unity 6.6 for static meshes: rotation 0, scale 1, facing +Z. The real criterion is the result in Unity: if an asset imports rotated, fix the export settings, not the instance in the scene.

- One asset per file, named after the asset (`Crate.fbx`). LODs use `_LOD0`, `_LOD1`, … suffixes.
- Export into the Unity project's art folder (`Assets/_Project/Art/...`) only when the user asked to; otherwise export next to the `.blend` file.
- **Instances.** Linked duplicates and collection instances export as one shared mesh, and Unity imports one Mesh for all of them, but only while no live modifier is applied on export and **Triangulate Faces** is off: apply modifiers and triangulation to the source mesh first. Export layouts as empties named after their assets, and replace them with prefab instances in Unity.

## Rigged and animated assets

`bake_space_transform` is documented by Blender as broken with armatures and animations, so rigs don't use the static mesh settings above. Start from them with these changes:

```python
    object_types={"MESH", "ARMATURE"},
    bake_space_transform=False,
    use_armature_deform_only=True,    # no control or helper bones in the game rig
    add_leaf_bones=False,
    bake_anim=True,                   # IK and constraints baked into keyframes
    use_mesh_modifiers=False,         # keeps shape keys
```

The axis settings that import a rig with rotation 0 and facing +Z depend on the Blender and Unity versions and aren't verified here. Export one test rig, check its rotation, scale, facing and animation in Unity, and record the settings that work in `docs/art-direction.md` for the rest of the project.

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

Load it in Unity with glTFast. Keep textures power-of-two. Blender writes PNG, JPEG or WebP only: GPU-compressed textures need KTX2 (`KHR_texture_basisu`) made with an external tool plus the KtxUnity package, and Draco mesh compression needs DracoForUnity.

## Unity import settings

Set them in the model's import settings, or with an `AssetPostprocessor` when every asset of a folder shares them:

- **Read/Write** off unless the CPU reads the mesh: code, a Mesh Collider, a Particle System Shape module or a Terrain detail. Unity 6.6 fails the build when one of those needs it and it's off. It's set per file, so keep collision meshes in their own files.
- **Mesh Compression** off by default: it only shrinks the file on disk, costs load time, can create artifacts and moves vertices slightly, which opens seams between modular pieces.
- **Import Cameras** and **Import Lights** off.
- **Materials:** don't use the embedded materials. Assign or remap to the project's materials.
- **Animation Type** None for static meshes (Unity otherwise imports them as Generic); **Import Animation** off.
- **Generate Colliders** off: colliders come from primitives or a dedicated collision mesh. It's acceptable only on static environment pieces whose render mesh is already simple.
- **Generate Lightmap UVs** on for static meshes in baked lighting without their own second UV set.
- Rigs: **Optimize Game Objects** on, **Skin Weights** at most 4.

## Check in Unity

Place the asset next to a 1 m reference cube, check its transform (rotation 0, scale 1) and facing (+Z), and capture the scene from several angles through the Unity CLI. Inspect every image before reporting.
