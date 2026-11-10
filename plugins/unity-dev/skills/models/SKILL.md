---
name: models
description: Brings 3D models, characters and clips from Blender into Unity - the export settings Unity needs and what they give, import settings, Humanoid bones and avatars, URP materials, LOD groups, colliders with their audit, prefabs placed as instances, glTF at runtime, and checks in the Editor.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
argument-hint: "[model or character]"
---

# 3D models in Unity

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

The models, characters and clips are made in Blender by `modeling:models`, `modeling:characters` and `modeling:animation`, with their checks. This guide takes them into Unity and proves them there; playing the clips is [animation](../animation/SKILL.md).

## Must

- **Imported as built:** the model root at rotation 0 and scale 1, facing +Z, at its real size next to a 1 m cube. An asset that imports rotated or scaled is fixed in the export settings, never on the instance in the scene.
- **Colliders:** what looks solid stops the player, nothing else does, and characters stand on the ground: [ColliderAudit](../library/code/Core/Editor/CostChecks/README.md#colliders) clean.
- **One asset, many instances:** each unique model is one prefab, placed many times. Never copies of it, never merged into one mesh ([performance](../performance/SKILL.md#repeated-objects)).

## Export settings

`export_fbx.py` (`modeling:models`) exports with these options by default, after the asset's checks pass; export through it rather than calling the exporter yourself. Static meshes:

```python
bpy.ops.export_scene.fbx(
    filepath="/abs/path/Crate.fbx",
    use_selection=True,
    object_types={"MESH"},            # "EMPTY" too for hierarchies and layout markers
    apply_scale_options="FBX_SCALE_ALL",
    apply_unit_scale=True,
    axis_forward="-Z",
    axis_up="Y",
    bake_space_transform=True,        # "Apply Transform": rotation 0 on import; broken with armatures
    use_mesh_modifiers=True,          # False for meshes with shape keys
    mesh_smooth_type="FACE",
    colors_type="LINEAR",             # vertex colors arrive as Blender rendered them
    add_leaf_bones=False,
    bake_anim=False,
    path_mode="STRIP",                # textures are imported separately
)
```

Rigged and animated assets start from the same options, with these changes:

```python
    object_types={"MESH", "ARMATURE"},
    bake_space_transform=False,
    use_armature_deform_only=True,    # no control or helper bones in the game rig
    bake_anim=True,                   # IK and constraints baked into keyframes
    bake_anim_use_all_actions=False,  # the current action; one clip per file: Character@Walk.fbx
    bake_anim_use_nla_strips=False,
    bake_anim_force_startend_keying=True,
    bake_anim_simplify_factor=0.0,    # no key reduction: reduced keys move planted feet and hands
    use_mesh_modifiers=False,         # only with shape keys; True otherwise
```

Verified with Blender 5.2.1 and Unity 6000.6.2f1:

- **A static mesh** imports with rotation 0 and scale 1, faces +Z, and its triangles face outward. Leave the model importer's **Bake Axis Conversion** off: with these settings it turns the asset around to face −Z.
- **A rig,** on a two-bone test rig whose action moves it forward and bends it: the model root imports with rotation 0 and scale 1, the mesh faces +Z, and the animation moves it along +Z. Under the root, the `Armature` and mesh objects carry an X rotation of −90° (shown as 270) and the root bone +90°. That is Blender's axis conversion, and together they are correct: never zero them. Bake Axis Conversion stays off here too: it turned the rig around to face −Z.
- After a Blender or Unity upgrade, or for a rig with IK, constraints or unusual bone rolls, export one test asset first and check it here, as [Check in Unity](#check-in-unity) describes.
- Export into the project's art folder (`Assets/_Project/Art/...`) only when the user asked to.

## Import settings

Set them in the model's import settings, or with an `AssetPostprocessor` when every asset of a folder shares them:

- **Read/Write** off unless the CPU reads the mesh: code, a Mesh Collider, a Particle System's Shape module (or its Renderer without GPU instancing) or a Terrain detail. Turn it on for those yourself. Unity 6000.6.2f1 still builds without it, with a warning that future versions won't handle it automatically, and its documentation already says the build fails. It's set per file, so keep collision meshes in their own files.
- **Pre-baked collision** on for meshes used by a Mesh Collider, so the build bakes their collision data instead of the game generating it at runtime: `ModelImporter.SetPreBakeCollisionMesh(isConvex, true)`, with `isConvex` true for a convex collider. The build warns about every Mesh Collider mesh without it. Verified on 6000.6.2f1: with Read/Write and pre-baked collision on, the build has no warnings.
- **Mesh Compression** off by default: it only shrinks the file on disk, costs load time, can create artifacts and moves vertices slightly, which opens seams between modular pieces.
- **Import Cameras** and **Import Lights** off.
- **Materials:** don't use the embedded materials. Assign or remap to the project's materials.
- **Animation Type** None for static meshes (Unity otherwise imports them as Generic); **Import Animation** off.
- **Generate Colliders** off: colliders come from primitives or a dedicated collision mesh. It's acceptable only on static environment pieces whose render mesh is already simple.
- **Generate Lightmap UVs** on for static meshes in baked lighting without their own second UV set.
- Unity counts more vertices than Blender: it splits them at UV seams and hard edges.

## Rigs and avatars

- **Animation Type** Humanoid for humanoid characters, Generic for everything else. Set **Avatar Definition** to **Create From This Model**, then turn **Optimize Game Objects** on. Unity 6.6 imports a Generic rig with no avatar, and without one the option does nothing. Bones that props or effects attach to go in **Extra Transforms to Expose**.
- **Humanoid bones:** 15 are required: Hips, Spine, Head, and on each side UpperArm, LowerArm, Hand, UpperLeg, LowerLeg and Foot. Optional: Chest, UpperChest, Neck, Shoulder, Toes, Eyes, Jaw, and three bones per finger; Unity fills in missing optional ones. A skeleton with fewer than the 15 is Generic only.
- **Names and sides.** Unity's automatic mapping reads `Left`/`Right`, or `L`/`R` set off by a space, `.`, `:`, `_` or `-` (`hand.L`, `hand_l`, `Left Hand`); Mixamo's `mixamorig:` names map too. A name for the wrong side scores −1000, but that check covers the body only, not the fingers. Unity then works out facing from the mapped bones: right is (RightUpperLeg − LeftUpperLeg) + (RightUpperArm − LeftUpperArm), and forward is right × up. Swapped sides therefore make the whole character face backward, with crossed or mirrored limbs.
- **Configure Avatar,** for every character:
  1. every required bone is mapped, Left bones on the character's own left, and the fingers to the right fingers, checked by hand;
  2. the pose is a T-pose, or Pose > Enforce T-Pose makes it one: Unity configures avatars in T-pose;
  3. in Muscles & Settings, move each slider through its range: no tearing, no limb crossing the body. When the arms cross the body in animation, narrow their ranges here, on the character's own avatar.
- **Skin Weights:** the model's setting, Standard (4 bones) by default, keeps the strongest influences and rescales them to 1. The project's Quality settings have their own limit.
- **Twist:** forearms and upper arms that collapse when they twist get twist bones, or the avatar's twist settings (`upperArmTwist`, `lowerArmTwist`).
- **Animator culling.** The Animator that Unity adds to a model with an avatar uses **Cull Update Transforms**: off screen, its transforms stop updating. A character whose bone positions gameplay reads while off screen needs **Always Animate**.
- **Variants:** an Edit Mode test holds the game's spawn table to the lists in the character's `inspect_character.py` receipt (`variant_groups`, `never_together`), so the game never combines what was never checked.

## Materials

- Blender's shader nodes don't reach Unity: build the materials in Unity with the URP shaders.
- **PBR maps for URP Lit:** metallic in R and smoothness in A of the metallic map, occlusion in G (one channel-packed texture can fill both slots). Smoothness is 1 − Blender's roughness. Data textures have sRGB off; normal maps are imported as Normal Map.
- Light baked into the asset draws with an unlit or Baked Lit shader ([performance](../performance/SKILL.md#light)).

## LODs

Authored levels with `_LOD0`, `_LOD1`, … suffixes (up to 8) are grouped by Unity's importer into a LOD Group: use them when the levels differ in materials or renderer settings. For geometry-only reduction, Unity's Mesh LOD generation on import (recent Unity 6 versions) uses less memory; it isn't for models that already have `_LODn` meshes.

## Colliders

- **Primitive colliders** (box, sphere, capsule, or a compound of them) first. A Mesh Collider only for static geometry, or convex (at most 255 triangles, `validate_mesh.py`'s default `CONVEX_LIMIT`) on a moving object, with the collision mesh `modeling:models` makes and checks, in its own file, with Read/Write and pre-baked collision on.
- **[ColliderAudit](../library/code/Core/Editor/CostChecks/README.md#colliders)** reads what ends up in scenes and in prefabs: colliders past the model, away from it, closing an opening in it or filling what can be walked to, primitives sheared under a parent scaled unevenly, Mesh Colliders with no mesh or moving and concave, a character that floats or sinks, whatever it stands on.
- For why a collision event doesn't fire, the official `unity:physics-3d-collision` skill.

## Placing in scenes

- Each unique model is one prefab, and a scene is built from its instances, placed through the Unity CLI. A layout drafted in Blender arrives as empties named after their assets: replace each with an instance of that prefab.
- Kit pieces built on the project's grid snap with Unity's grid snapping.
- Unity's primitives are for blockouts and shapes they match exactly: its Plane is 10 m wide with 200 triangles.

## glTF at runtime

Models loaded at runtime come as glTF, loaded with glTFast. GPU-compressed textures need KTX2 files and the KtxUnity package; Draco mesh compression needs DracoForUnity.

## Check in Unity

Place the asset next to a 1 m reference cube. Check the model root's transform (rotation 0, scale 1; a rig's children keep the conversion described above) and its facing (+Z). Capture the scene from several angles through the Unity CLI, and in the game from its real camera, and inspect every image before reporting. A character is captured with each hat and hair the game can spawn.
