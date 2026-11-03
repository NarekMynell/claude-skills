# Rigging and skinning for Unity Humanoid

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

`inspect_character.py` checks most of the rules below; this page explains them and how to fix what it reports.

## Skeleton

- **Required bones:** Unity Humanoid needs 15: Hips, Spine, Head, and on each side UpperArm, LowerArm, Hand, UpperLeg, LowerLeg and Foot. Optional: Chest, UpperChest, Neck, Shoulder, Toes, Eyes, Jaw, and three bones per finger. Unity fills in missing optional bones.
- **Hierarchy follows the body:** Hips, Spine, Chest, Neck, Head in a chain; UpperLeg under the Hips; UpperArm under the Shoulder or the Chest; each limb a chain down to its hand or foot. A root bone above the Hips is fine.
- **Names and sides.** Unity's automatic mapping reads `Left`/`Right`, or `L`/`R` set off by a space, `.`, `:`, `_` or `-` (`hand.L`, `hand_l`, `Left Hand`). A name for the wrong side scores −1000, but that check covers the body only, not the fingers. Unity then works out facing from the mapped bones: right is (RightUpperLeg − LeftUpperLeg) + (RightUpperArm − LeftUpperArm), and forward is right × up. Swapped sides therefore make the whole character face backward, with crossed or mirrored limbs. Check the finger mapping by hand in Configure Avatar.
- **Blender side:** the character faces −Y and its left is +X, so `.L` bones sit at +X; Blender's AutoName works the same way. `inspect_character.py` reports `left_right_swapped` and `not_facing_minus_y`.
- **Rest pose:**
  - T-pose, or A-pose with the arms up to 45° below horizontal;
  - palms down and thumbs forward: a left hand that only looks right with the palm up is mirrored geometry;
  - fingers slightly apart and gently curved;
  - legs straight and a little apart;
  - feet flat on the ground at z = 0, origin between them.

  Unity configures avatars in T-pose, and Enforce T-Pose turns an A-pose into one.
- **Joints in the right places:** each bone's head at the joint's center of rotation (shoulder, elbow, wrist, hip, knee, ankle, knuckles), elbows bent slightly backward and knees slightly forward. A joint off its center bends the mesh at the wrong place.
- **Bone rolls:** consistent along each limb and mirrored between the sides. Build or fix one side, then symmetrize.
- **Deform bones only** reach Unity (`use_armature_deform_only`); control, IK and helper bones stay in Blender. The exporter still writes a non-deforming bone that has a deform bone as its child, so every deform bone's parent must deform too. A raw Rigify rig fails that; game rigs (MPFB `game_engine`, Mixamo) pass.
- **Bone count:** every bone costs animation time. A full humanoid with fingers is about 50–65 bones; a character that never holds anything can drop the finger bones.

## Weights

- **Automatic weights** (bone heat) need a clean surface: closed, manifold, no internal faces or overlapping shells, normals outward, scale applied, limbs and fingers apart. When it reports "failed to find solution", fix the mesh, not the weights: merge by distance, recalculate normals, dissolve degenerate geometry, separate stray parts.
- **Clean up every automatic result,** then check it:
  ```python
  bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
  bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
  ```
  `lock_active` defaults to True, which leaves the active group out of the normalization. Remove weight from the other side's bones outside the center strip: it's how the legs end up moving together.
- **Unity:** the model's Skin Weights setting, Standard (4 bones) by default, keeps the strongest influences and rescales them to 1. The project's Quality settings have their own Skin Weights limit.
- **Joints:** weights blend across a joint over its edge loops, at least three at elbows and knees, wider at shoulders and hips. Twisting forearms and upper arms collapse like a candy wrapper under linear blend skinning: add twist bones, or rely on Unity's twist settings (`upperArmTwist`, `lowerArmTwist` in the avatar's settings).
- **Preserve Volume** in Blender's Armature modifier doesn't reach Unity, which skins linearly: keep it off while judging deformation.

## Clothes and attachments

- **Clothes take the body's weights.** Select the clothes, make the body active, then:
  ```python
  bpy.ops.object.data_transfer(data_type="VGROUP_WEIGHTS", use_create=True, vert_mapping="POLYINTERP_NEAREST",
                               layers_select_src="ALL", layers_select_dst="NAME")
  ```
  Then limit to 4, normalize, and check the test poses. Loose garments such as skirts and long coats transfer better with the free Robust Weight Transfer add-on (version 1.1.9 has Blender 5.0 and 5.1 builds; check 5.2 support before using it).
- **Rigid parts** such as helmets, armor plates and holstered items are weighted fully to one bone, or parented to a bone.
- **Clearance:** clothes and attachments sit 2–5 mm outside the body. Closer, the body pokes through when it bends; farther, the gap shows.

## Test poses

`inspect_character.py` bends the rig into arms down, arms up, arms forward, squat, stride, twist and fists, then reports parts that poke through each other (`poke_through_in_poses`) and edges stretched past twice or shrunk below a third of their rest length (`stretched_in_poses`, usually wrong weights). Render the same poses as a sheet and look at:

- elbows and knees keeping their volume, with no collapse or candy wrapper;
- shoulders with the arms up: no tearing or caving;
- hips and crotch in the squat and stride;
- fingers curling without breaking into each other;
- clothes staying over the body in every pose.

## In Unity

1. Import as Humanoid with Create From This Model, then open Configure Avatar.
2. Every required bone is mapped to the right side, and the fingers to the right fingers.
3. The pose is a T-pose, or Pose > Enforce T-Pose makes it one.
4. In Muscles & Settings, move each slider through its range: no tearing, no limb crossing the body. When the arms cross the body in animation, narrow their ranges here, on the character's own avatar.
