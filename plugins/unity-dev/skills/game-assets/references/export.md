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

Verified with Blender 5.2.1 and Unity 6000.6.2f1: a static mesh imports with rotation 0 and scale 1, faces +Z, and its triangles face outward. Leave the model importer's **Bake Axis Conversion** off: with these settings it turns the asset around to face −Z. The real criterion is the result in Unity: if an asset imports rotated, fix the export settings, not the instance in the scene.

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

Verified with Blender 5.2.1 and Unity 6000.6.2f1 on a two-bone test rig whose action moves it forward and bends it: the model root imports with rotation 0 and scale 1, the mesh faces +Z, and the animation moves it along +Z. Under the root, the `Armature` and mesh objects carry an X rotation of −90° (shown as 270) and the root bone +90°. That is Blender's axis conversion, and together they are correct: never zero them. Bake Axis Conversion stays off here too: it turned the rig around to face −Z.

For a rig with IK, constraints or unusual bone rolls, or after a Blender or Unity upgrade, export one test asset first. Check its rotation, scale, facing and animation in Unity, and record the settings that work in `docs/art-direction.md`.

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

- **Read/Write** off unless the CPU reads the mesh: code, a Mesh Collider, a Particle System's Shape module (or its Renderer without GPU instancing) or a Terrain detail. Turn it on for those yourself. Unity 6000.6.2f1 still builds without it, with a warning that future versions won't handle it automatically, and its documentation already says the build fails. It's set per file, so keep collision meshes in their own files.
- **Pre-baked collision** on for meshes used by a Mesh Collider, so the build bakes their collision data instead of the game generating it at runtime: `ModelImporter.SetPreBakeCollisionMesh(isConvex, true)`, with `isConvex` true for a convex collider. The build warns about every Mesh Collider mesh without it. Verified on 6000.6.2f1: with Read/Write and pre-baked collision on, the build has no warnings.
- **Mesh Compression** off by default: it only shrinks the file on disk, costs load time, can create artifacts and moves vertices slightly, which opens seams between modular pieces.
- **Import Cameras** and **Import Lights** off.
- **Materials:** don't use the embedded materials. Assign or remap to the project's materials.
- **Animation Type** None for static meshes (Unity otherwise imports them as Generic); **Import Animation** off.
- **Generate Colliders** off: colliders come from primitives or a dedicated collision mesh. It's acceptable only on static environment pieces whose render mesh is already simple.
- **Generate Lightmap UVs** on for static meshes in baked lighting without their own second UV set.
- **Rigs:** set **Avatar Definition** to **Create From This Model**, then turn **Optimize Game Objects** on. Unity 6.6 imports a Generic rig with no avatar, and without one the option does nothing. Bones that props or effects attach to go in **Extra Transforms to Expose**. **Skin Weights** at most 4.
- **Animator culling.** The Animator that Unity adds to a model with an avatar uses **Cull Update Transforms**: off screen, its transforms stop updating. A character whose bone positions gameplay reads while off screen needs **Always Animate**.

## Check in Unity

Place the asset next to a 1 m reference cube. Check the model root's transform (rotation 0, scale 1; a rig's children keep the conversion described above) and its facing (+Z). Capture the scene from several angles through the Unity CLI, and inspect every image before reporting.
