---
name: characters
description: Creates the project's own game-ready characters and animals for Unity through Blender - transformed professional bases or skeleton-first bodies built from scratch, single-layer clothes and hair, variants that fit each other, Humanoid rigging and skinning, and automated anatomy, penetration, weight and deformation checks with reviews from the game's camera.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
argument-hint: "[character]"
---

# Game characters

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

Read [game assets](../game-assets/SKILL.md) first: its way of working, scripts, review loop and export apply here. Motion: [animation](../animation/SKILL.md).

## Must

- **Nothing pokes through anything,** as the player sees it. No head through a hat, no hair through a hat, no skin through clothes, no limb through the body, in any combination of variants the game can show, in any pose it uses, from any angle the camera reaches. Parts that overlap where they join don't poke: a leg that enters a torso and stays there is one way to build a body. An arm that comes out the other side is a poke.
- **Every character passes** `validate_mesh.py` and `inspect_character.py`, with all its parts in `TARGETS` and all its variants in `PART_GROUPS`; its review finds nothing left to fix, including from the game's own camera; it deforms cleanly in the test poses and in its animations.
- **The proof holds on any pipeline.** A character built by a custom script, merged into one mesh, or skinned in a shader goes through the same checks: build it as Blender objects with an armature, and run them. A check of your own counts only when it catches the same defects: a count of coplanar faces catches none of these. Run it with `PROOF_DIR` set to the project's `docs/proofs`, so each character leaves its receipt.
- **The characters are the project's own.** A third-party character never ships as it came, unless the user asks for that model: a base is a starting point, changed until it is this project's design.

The method for each character is a guide: your choice, from this guide or outside it, whatever gives the best result for the project's style, budget and schedule. Tell the user the choice and why, without handing it back, and record project-wide choices under **Decisions** in the project's `CLAUDE.md`. A method that can't reach the bar is the wrong method.

**What has failed:**

- Bodies built from primitives, metaballs or vertex moves in code, and sculpting through screenshots: fused legs, bloated waists, crooked hands, wrong faces, and tweaking didn't fix them. Use a method like that only with a concrete reason it will work this time, proven by the checks on an early blockout.
- Variants in a real project: a sun hat whose crown was smaller than the hair under it, so the head came out through the top. It looked fine from the front. No check had run on it, the reviews never looked from above, and the game's camera looks from above.
- A check that fails everything: a real project of 73 characters built from parts failed the earlier version of `inspect_character.py` on 71 of them, because it took any crossing for a poke. Failing every character, it couldn't show a real defect. When a check fails what looks right, read what it reports and say so, with what the player would see: a wrong check is reported and fixed, not ignored or worked around.

Methods known to work:

1. **Transform a professional base:** a body whose topology, proportions and rig are already right, changed through its own controls into the project's character ([section 3](#3-make-it-the-projects-own)).
2. **Build from scratch, skeleton first:** a joint skeleton with a thickness at each joint becomes the surface ([build_body.py](../game-assets/scripts/build_body.py)), so limbs stay apart and the sides mirror; the design is added as parts modeled like props. Method and limits: [references/from-scratch.md](references/from-scratch.md).
3. **Build from parts:** solid parts that overlap at the joints, modeled like props, for styles where the joints are meant to show. Recipe, cost and failures: [references/from-parts.md](references/from-parts.md).

Other routes are open: another add-on or generator, a model the user bought, a tool the user owns, a retopologized scan. The same bar applies.

## 1. Brief

Settle these with the user and record them in `docs/art-direction.md` before choosing the method:

- **Style and proportions**, in head heights: realistic 7.5, idealized 8, heroic 8.5, stylized about 4–6, chibi 2–3. One style per project.
- **Triangle budget** for the target platform, and the LOD count. As a reference, VRChat's performance ranking rates mobile avatars Excellent up to 7,500 triangles with one skinned mesh and one material, and Poor at 20,000; PC avatars Excellent up to 32,000 and Good up to 70,000. Any budget: one skinned mesh, as few materials as possible.
- **Layers.** One layer by default: the character is one visible surface, and the body faces under clothes are deleted. Keep the body under clothes only when outfits swap at runtime or the body shows without them. Hidden geometry costs triangles and pokes through when the character moves.
- **What it does:** the clips from the animation plan, the props it holds, whether the face animates. These decide finger bones, face bones and shape keys.
- **References:** the user's images, or a written front and side description; real anatomy for realistic characters.

## 2. Choose the method

Starting points, not a closed list; the brief decides.

| Character | Usually best | Notes |
|---|---|---|
| Realistic or semi-realistic human | Transform an MPFB body | Correct anatomy, faces and hands; clothes that hide the body under them; low-poly proxies for budgets |
| Stylized human with a detailed face, low or mid poly | Transform a stylized base (Quaternius, Kenney), or an MPFB body with stylized proportions | Faces and hands are where scratch-built characters fail |
| Cartoon or abstract humanoid with a simple face or none | From scratch, skeleton first | Proportions free: big heads, short legs, mitten hands |
| Robot, blocky, toy-like, hard-surface creature | [From parts](references/from-parts.md) | Rigid parts weighted to one bone each |
| Toy-like or low-poly people and animals, where a crease at each joint is part of the look | [From parts](references/from-parts.md) | Cheap to build and to vary. Reads as a toy: the art direction must want that |
| Animal or creature | Skeleton first when its forms are simple; from parts when the look allows; otherwise a professional base | Checks and bends fit any skeleton: no human bones asked for |
| Anime | VRoid Studio, run by the user, exported as VRM, then transformed | |
| A character the user owns, bought or asks for by name | That model, as the user wants it | |

When no listed source fits, look for one: a license that allows changes and commercial use (CC0, or CC-BY with credit), a clean humanoid skeleton, a budget near the target. Details, licenses, downloads and the MPFB recipe: [references/sources.md](references/sources.md). Downloads that need a browser, an account or a payment are the user's to do. Record every third-party asset in `docs/third-party-assets.md`.

AI 3D generators (Meshy, Tripo, Rodin, Hunyuan3D, TRELLIS) are no base for main animated characters: they guess the hidden side, bake lighting into the textures, leave messy UVs, rig hands and faces unreliably, and their licenses depend on the plan or the region. They suit concepts, props and distant background figures, after the same checks.

## 3. Make it the project's own

- **Silhouette and proportions** through the base's controls: MPFB's sliders and targets, shape keys, bone lengths before binding, or the joints and thicknesses of a skeleton-first body. Never by moving vertices one by one in code.
- **Face:** the base's face targets and shape keys, or, for a cartoon face, eyes, brows, nose and mouth modeled as parts and fitted to the head.
- **Hair, clothes and accessories** designed for this character, modeled like props, then fitted: 2–5 mm above the surface, never cutting into it, taking the body's weights ([rigging](references/rigging.md#clothes-and-attachments)). Swap a base's part for another rather than bending one into another.
- **Colors and textures** from the project's palette and art direction, made on purpose by the game-assets rules.
- **One layer:** delete the body faces each garment covers, keeping a ring under its edges so no gap opens when it moves. `inspect_character.py` lists the covered faces; MPFB's delete groups remove them for its own clothes.
- **Hair:** a solid hair mesh sits 2–5 mm above the scalp, never inside it, and the scalp it covers completely is deleted. Hair cards, transparent strips, need a hair-colored scalp under them; list them in `SEE_THROUGH`. Hair is weighted to the head, and to the neck and spine for long hair.
- **Hands and feet** are where changes break bodies: keep a base's own, changed only with its controls.
- **Variants** (hair, hats, glasses, bags) are the project's cheapest variety and its most common defect. Each pair from different groups must fit, or the game must never combine them:
  - a hat is modeled around the largest hair it can sit on, or hair has a version for hats: the part under the hat is cut away, or replaced by a short cap;
  - list every interchangeable part in `PART_GROUPS`, and pairs the game never combines in `NEVER_TOGETHER`. An Edit Mode test holds the game's spawn table to the lists in the receipt (`variant_groups`, `never_together`), so the game can't combine what was never checked;
  - from above and from the game's camera, on every hat: nothing of the head or hair shows through. `shows_through_from_above` looks straight down inside the outline of whatever sits on the head, at every other part it can appear with, and finds what cuts no surface: a head out of an open crown, a hat lost in hair. `open_part` finds holes above a hat's rim, which a look from the game's camera would meet;
  - a pipeline that merges a variant into one mesh runs the script on each merged result: each island is a surface, and `self_intersections` then reports the clash.
- **Budget:** a lower-poly topology of the base, such as an MPFB proxy, or fewer subdivisions of a skeleton-first body, instead of decimating. Decimation destroys the edge loops joints need to bend. LODs: decimate a copy with symmetry on and UV seams kept, then check its deformation again.

## 4. Rig and skin

Unity's Humanoid system retargets any humanoid animation onto any humanoid character, so every humanoid rig aims at it. Requirements, names, rest pose, weights and attachments: [references/rigging.md](references/rigging.md). In short:

- The character faces −Y in Blender, its left side at +X. Left bones carry a left marker (`.L`, `_l`, `Left`) and sit at +X. Unity reads facing and sides from them: a swap gives a character that faces backward or crosses its limbs.
- Rest pose: T- or A-pose, palms down, thumbs forward, fingers and legs apart, feet flat on the ground at z = 0, origin between the feet.
- The 15 required Humanoid bones, and three bones per finger when the character holds anything. Only deform bones go to Unity.
- Every vertex weighted, at most 4 influences, normalized, no weight from the other side's bones.

## 5. Check

All of the character's meshes together, every round:

1. [validate_mesh.py](../game-assets/scripts/validate_mesh.py) with the triangle budget.
2. [inspect_character.py](../game-assets/scripts/inspect_character.py), set for the design: `SINGLE_LAYER`, `ALLOW_HIDDEN` for eyes and mouth parts that animate, `SEE_THROUGH` for hair cards, `TWO_SIDED` for what a two-sided material draws, `SYMMETRIC` for the body, `FINGERS`, `PART_GROUPS` for variants, and `LEGS_JOINED`, `WAIST_BULGE`, `ALLOW_CROSSING` or `ALLOW_FLOATING` only when the design asks for them. It works on connected surfaces, whatever the objects: one skin, separate parts or one merged mesh. It checks:
   - **anatomy:** legs separate, on any number of them; for a person, up to the crotch, and no waist wider than hips and chest; symmetry; feet on the ground;
   - **what shows wrong:** surfaces no joint connects cutting each other, a part out of the far side of what it enters, a surface that runs under another showing through it (`parts_intersect`, `self_intersections` in one mesh), variants that do the same or are lost in each other (`variants_clash`, `variant_swallowed`), what shows through a hat or holes in it (`shows_through_from_above`, `open_part`, `inside_out`, `top_not_on_head`; `COVERS_FROM_ABOVE` adds what covers the head, `OPEN_ON_TOP` takes away a tiara or a headband), openings that show a surface's inside (`see_inside`), parts hanging in the air (`floating_part`), and meshes on the rig left out of `TARGETS` (`parts_left_out`);
   - **what stays hidden,** at rest and in every pose: faces inside a mesh, parts sunk into the body, covered body faces (`hidden_inside`, `sunk_into_body`, `covered_faces`). It fails from 5% of the triangles, or most of an object buried: a mouth's few hidden faces cost less than finding them;
   - **feet:** on the ground, and each of them (`not_on_ground`, `foot_off_ground`; `GROUND = None` for what swims or flies);
   - **rig:** for a person, Humanoid bones, sides, facing, hierarchy, rest pose, thumbs in front, finger order; for an animal or creature, sides and facing (`HUMANOID` overrides which: by default, enough Humanoid bones, standing upright). A rig imported from FBX, with tails that point anywhere and a file's unit scale over it, is read as what it is;
   - **weights:** unweighted vertices, weight from the opposite side by where the bone stands, and more than 4 influences where the ones Unity drops carry over a tenth of the weight;
   - **deformation:** test poses for a person (arms down, up and forward, squat, stride, twist, fists), and for any other body its legs forward, back and folded, and its trunk, neck and tail to the side, up and down: what a pose brings through what (`poke_through_in_poses`), joints that come apart (`joint_opens_in_poses`), openings that show the inside (`see_inside_in_poses`), stretched or collapsed edges.

   Each issue's `examples` give positions, and for crossings the reason: fix the cause there. When a report seems wrong, render that spot before believing either side.
3. **Contact sheets** with [render_views.py](../game-assets/scripts/render_views.py):
   - `PRESET="CHARACTER"`, with `GRID` set to the style's head count: front, back, both sides, two 3/4 views, top, and close-ups of the face, the top of the head, both hands from above, a palm and the feet, in one image;
   - `GAME_VIEW` set to the game camera's angle and `GAME_PIXELS` to the character's height on a phone, on every variant the player can see: this is what the player gets, and the only tile that decides whether a detail is worth its triangles;
   - the same with `WIREFRAME=True` and `LIGHT="MATCAP"`, `COLOR="SINGLE"` for topology and surface;
   - the deformation: key the test poses on frames of a temporary action, render them with `FRAMES`, then delete the action.
4. **Critique** against the [character review](references/review.md), region by region.

Fix every finding at its cause. A pose that stretches means bad weights, not a pose to avoid; hair in the head means the hair mesh moves out, not a material that hides it.

## 6. Export and check in Unity

[export_fbx.py](../game-assets/scripts/export_fbx.py) runs both checks again and exports with the rigged settings ([export reference](../game-assets/references/export.md#rigged-and-animated-assets)). In Unity, import the model as Humanoid ([animation guide](../animation/SKILL.md#3-import-in-unity)) and open **Configure Avatar**:

- every required bone is mapped, Left bones on the character's own left;
- the pose is a T-pose, or Pose > Enforce T-Pose makes it one;
- the Muscles & Settings preview moves every limb through its range without tearing or crossing the body.

Capture the character in the scene next to a 1 m cube, and in the game from its real camera at its real zoom levels, with each hat and hair the game can spawn, and review the images. Tell these apart from studio renders: lighting, shader and distance differ, and it is the game that counts.
