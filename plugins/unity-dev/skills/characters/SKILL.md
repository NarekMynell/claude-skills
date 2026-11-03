---
name: characters
description: Creates game-ready characters for Unity through Blender - a professional base instead of anatomy modeled from scratch, customization, single-layer clothes and hair, Humanoid rigging and skinning, and automated anatomy, penetration, weight and deformation checks with multi-angle reviews.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
argument-hint: "[character]"
---

# Game characters

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

Read [game assets](../game-assets/SKILL.md) first: its way of working, scripts, review loop and export apply here. Motion: [animation](../animation/SKILL.md).

## The rule that matters most

Never build a human or animal body from primitives, metaballs or vertex moves in code, and never sculpt one through screenshots. Code can't describe anatomy: such bodies come out with fused legs, bloated waists, crooked hands and wrong faces, and tweaking doesn't fix them. Start from a professionally made base, whose topology, proportions and rig are already right, and change it only through its own controls. Build from scratch only what is simple by design: blocky or toy-like figures, robots, and creatures made of hard parts.

## 1. Brief

Settle these with the user and record them in `docs/art-direction.md` before choosing a base:

- **Style and proportions**, in head heights: realistic 7.5, idealized 8, heroic 8.5, stylized about 4–6, chibi 2–3. One style per project.
- **Triangle budget** for the target platform, and the LOD count. As a reference, VRChat's performance ranking rates mobile avatars Excellent up to 7,500 triangles with one skinned mesh and one material, and Poor at 20,000; PC avatars Excellent up to 32,000 and Good up to 70,000. Any budget: one skinned mesh, as few materials as possible.
- **Layers.** One layer by default: the character is one visible surface, and the body faces under clothes are deleted. Keep the body under clothes only when outfits swap at runtime or the body shows without them. Hidden geometry costs triangles and pokes through when the character moves.
- **What it does:** the clips from the animation plan, the props it holds, whether the face animates. These decide finger bones, face bones and shape keys.
- **References:** the user's images, or a written front and side description; real anatomy for realistic characters.

## 2. Choose the base

| Character | Start from | Why |
|---|---|---|
| Realistic or semi-realistic human | MPFB, MakeHuman for Blender: body from sliders, clothes, hair, a rig Unity maps | Correct anatomy and topology; its clothes hide the body under them; scriptable; CC0 assets |
| Stylized human | Quaternius Universal Base Characters, Kenney Animated Characters, or the project's own base | Clean bodies with a humanoid skeleton, free for commercial games |
| Anime | VRoid Studio, run by the user, exported as VRM | Made for the style |
| A character the user owns or bought | That model | After the same checks |
| Blocky, toy-like, robot, hard-surface creature | Code: parts modeled like props, rigid or simply skinned | Simple by design |
| Organic creature with no base | The user decides: a bought or commissioned model, or a generated one retopologized and checked like any base | |

Details, licenses, downloads and the MPFB scripting recipe: [references/sources.md](references/sources.md). Tell the user which base you chose and why, and record every third-party asset in `docs/third-party-assets.md`.

AI 3D generators (Meshy, Tripo, Rodin, Hunyuan3D, TRELLIS) are no base for main animated characters: they guess the hidden side, bake lighting into the textures, leave messy UVs, rig hands and faces unreliably, and their licenses depend on the plan or the region. They suit concepts, props and distant background figures, after the same checks.

## 3. Customize without breaking it

- **Proportions through the base's controls:** MPFB's sliders and targets, shape keys, or bone lengths before binding. Never by moving vertices in code.
- **Swap parts, don't reshape them:** another fitted hairstyle, outfit, head or hands rather than one bent into another.
- **New parts** (armor, hat, belt, pouch) are modeled like props, then fitted: they follow the surface 2–5 mm above it, never cut into it, and take the body's weights ([rigging](references/rigging.md#clothes-and-attachments)).
- **One layer:** delete the body faces each garment covers, keeping a ring under its edges so no gap opens when it moves. `inspect_character.py` lists the covered faces; MPFB's delete groups remove them for its own clothes.
- **Hair:** a solid hair mesh sits 2–5 mm above the scalp, never inside it, and the scalp it covers completely is deleted. Hair cards, transparent strips, need a hair-colored scalp under them; list them in `SEE_THROUGH`. Hair is weighted to the head, and to the neck and spine for long hair.
- **Hands and feet** are where customization breaks bases: keep the base's own, changed only with its controls.
- **Budget:** a lower-poly topology of the base, such as an MPFB proxy, instead of decimating. Decimation destroys the edge loops joints need to bend. LODs: decimate a copy with symmetry on and UV seams kept, then check its deformation again.
- **Materials and textures:** as few as possible; the base's own, or made on purpose by the game-assets rules.

## 4. Rig and skin

Unity's Humanoid system retargets any humanoid animation onto any humanoid character, so every humanoid rig aims at it. Requirements, names, rest pose, weights and attachments: [references/rigging.md](references/rigging.md). In short:

- The character faces −Y in Blender, its left side at +X. Left bones carry a left marker (`.L`, `_l`, `Left`) and sit at +X. Unity reads facing and sides from them: a swap gives a character that faces backward or crosses its limbs.
- Rest pose: T- or A-pose, palms down, thumbs forward, fingers and legs apart, feet flat on the ground at z = 0, origin between the feet.
- The 15 required Humanoid bones, and three bones per finger when the character holds anything. Only deform bones go to Unity.
- Every vertex weighted, at most 4 influences, normalized, no weight from the other side's bones.

## 5. Check

All of the character's meshes together, every round:

1. [validate_mesh.py](../game-assets/scripts/validate_mesh.py) with the triangle budget.
2. [inspect_character.py](../game-assets/scripts/inspect_character.py), set for the design: `SINGLE_LAYER`, `ALLOW_HIDDEN` for eyes and mouth parts that animate, `SEE_THROUGH` for hair cards, `SYMMETRIC` for the body, `FINGERS`, and `LEGS_JOINED` or `WAIST_BULGE` only when the design asks for them. It checks:
   - **anatomy:** legs separate up to the crotch, no waist wider than hips and chest, symmetry, feet on the ground;
   - **surfaces:** faces hidden inside a mesh, parts sunk into the body (hair in the head), covered body faces, intersecting parts;
   - **rig:** Humanoid bones, sides, facing, hierarchy, rest pose, thumbs in front, finger order;
   - **weights:** unweighted vertices, more than 4 influences, weight from the opposite side;
   - **deformation** in test poses (arms down, up and forward, squat, stride, twist, fists): parts that poke through each other, stretched or collapsed edges.

   Each issue's `examples` give positions: fix the cause there.
3. **Contact sheets** with [render_views.py](../game-assets/scripts/render_views.py):
   - `PRESET="CHARACTER"`, with `GRID` set to the style's head count: front, back, both sides, two 3/4 views, and close-ups of the face, both hands from above, a palm and the feet, in one image;
   - the same with `WIREFRAME=True` and `LIGHT="MATCAP"`, `COLOR="SINGLE"` for topology and surface;
   - the deformation: key the test poses on frames of a temporary action, render them with `FRAMES`, then delete the action.
4. **Critique** against the [character review](references/review.md), region by region.

Fix every finding at its cause. A pose that stretches means bad weights, not a pose to avoid; hair in the head means the hair mesh moves out, not a material that hides it.

## 6. Export and check in Unity

[export_fbx.py](../game-assets/scripts/export_fbx.py) runs both checks again and exports with the rigged settings ([export reference](../game-assets/references/export.md#rigged-and-animated-assets)). In Unity, import the model as Humanoid ([animation guide](../animation/SKILL.md#3-import-in-unity)) and open **Configure Avatar**:

- every required bone is mapped, Left bones on the character's own left;
- the pose is a T-pose, or Pose > Enforce T-Pose makes it one;
- the Muscles & Settings preview moves every limb through its range without tearing or crossing the body.

Capture the character in the scene from several angles next to a 1 m cube and review the images.
