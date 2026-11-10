---
name: animation
description: Makes natural animation clips in Blender for characters and animals - the clip plan, library sources, motion keyed by the craft's rules when nothing fits, automated checks of foot contact, speed, gaits, robotic motion, loops and penetration, filmstrip reviews, and export.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/modeling/**)
argument-hint: "[character or motion]"
---

# Animation clips

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

The character comes from the [characters](../characters/SKILL.md) guide; the scripts and the review loop from [models](../models/SKILL.md). Playing the clips in the engine, with speeds that keep the feet planted, the ground and held props, is the engine's guide, and so is the proof in the running game (Unity: `unity-dev:animation`).

## Must

- **Natural on the rig.** Speed fits the body. Weight, overlap and follow-through are there; nothing is robotic. Planted feet stay still and on the ground. Hands stay out of the body and out of props.
- **Checked.** Every clip passes `inspect_animation.py`, and a filmstrip review finds nothing left. Motion on a custom pipeline or in a shader passes the same checks ([how](references/motion-craft.md#how-to-key-it)). A clip's numbers prove nothing about the game: the engine's check in the running game follows (Unity: `unity-dev:animation`). Without an engine domain, review a capture of the clip playing in the target engine, and report the game-side proof as missing.
- **Known defects get fixed,** not deferred until someone sees them.

The method for each motion is a guide: your choice, inside this guide or outside it, for the best result in this project. Tell the user the choice and why, and record project-wide choices under **Decisions** in the project's `CLAUDE.md`.

**What has failed, twice.** Human motion keyed by code came out robotic, with sliding or floating feet and hands through the body. Then a project built skeleton motion for people and animals in code, with a good pipeline and clip speeds matched to the feet, and its owner still called it robotic, dry and sliding: it had checked only its clips' numbers, deferred the worst slides, had no weight or overlap, and pushed actors sideways in the game.

**What works:** motion capture or professional libraries for people, retargeted onto the character by the engine's humanoid system; for animals and for cartoon proportions, libraries where they fit ([sources](#2-sources)), or motion keyed with the [motion craft](references/motion-craft.md) rules.

## 1. Plan the clips

List every clip the game needs before getting any: idle; walk and run at their speeds; turns; jump start, loop and landing; stairs up and down if the levels have stairs; interactions such as pick up, open, hold and throw; hit and death. For each one record in `docs/art-direction.md`:

- whether it loops;
- root motion or in place, as the engine's guide decides (Unity: `unity-dev:animation`);
- the speed it moves at;
- the props it uses, and a grip pose for each kind of prop: one frame keyed on the character's rig with the fingers closed around the handle, checked with `PROPS` (`hand_through_prop`).

## 2. Sources

| Source | License | Notes |
|---|---|---|
| Quaternius Ultimate Animated Animal Pack | CC0 | 12 animals with more than 12 animations each, walk and gallop among them; the user downloads. Check what's rigged |
| Kenney Animated Characters | CC0 | Humans; check the animations |
| Truebones Zoo | Free, royalty-free for commercial use by its Gumroad page, no redistribution of the files, credit asked; read the terms before use | Over 75 animated animals, FBX |
| Mixamo | Free with an Adobe ID; royalty-free in games; the files can't be redistributed | The user downloads in the browser. FBX (FBX for Unity in a Unity project), Without Skin, 30 fps, keyframe reduction off; In Place for clips the code moves |
| Quaternius Universal Animation Library 1 and 2 | QAL v1.0: commercial use, no redistribution of the files ([details](../characters/references/sources.md#quaternius-stylized-humans-and-animation)) | Root-motion and in-place versions; the user downloads |
| CMU motion capture | Commercial use allowed, no resale, even converted | BVH, imported into Blender; avoid the 4TU FBX conversion, which is CC BY-NC |

Downloads are the user's: list the clips the game needs and ask for them at the start of the work, before the user goes away. For humans especially, keying by code is the method that has failed twice. When a brief forbids third-party content, or nothing can be downloaded, key with the [motion craft](references/motion-craft.md) rules, to the same bar, and report such motion as unproven until the user has seen it moving: send them a capture, and name it as the first thing to judge. Record every clip in `docs/third-party-assets.md`. Mixamo's Character Arm-Space setting widens the arms before download, for bulky characters whose arms would cut the body. An engine can have sources of its own (Unity: `unity-dev:animation`).

## 3. Keying in Blender

For what is keyed by hand: block the key poses (contacts and extremes), then the breakdowns; arcs, ease in and out, and overlapping motion for secondary parts. Keep planted feet still in world space (IK, or Copy Global Transform, a Blender core feature since 5.0), and contacts on whole frames. Edits to library clips happen on the clip's own rig, at its own frame rate. The numbers a walk is made of, and how code-made motion stops looking robotic: [motion craft](references/motion-craft.md).

## 4. Check

1. **Every clip in Blender, on the character's rig:** [inspect_animation.py](../../scripts/inspect_animation.py) reports:
   - planted feet that slide, feet below the ground or never reaching it;
   - for in-place clips, the speed the character must move at (`stride_speed_mps`) and the direction (`move_direction`);
   - the speed against the body (`froude`, `natural_walk_speed_mps`, `too_fast_for_a_walk`) and against the game (`GAME_SPEED`, `playback_rate_out_of_range`);
   - steps out of rhythm, and on four legs the gait and footfall order (`FEET`, `GAIT`, `wrong_gait`, `irregular_footfall`);
   - clips where no foot could be measured (`feet_not_measured`): hair and bags don't count as the body, and `BODY` settles it;
   - robotic motion: `no_pelvis_motion`, `trunk_still`, `stiff_knees`, `arms_hang_still`, `linear_motion`, `everything_moves_together`, `secondary_still`, `frozen`. `NATURAL=False` turns these off for machines;
   - arms swinging with the same-side leg;
   - loop seams and joint pops;
   - what the clip brings through what (`limbs_through_body`): surfaces with no joint between them, such as a hand in a hip or legs through each other, and layers on the same bones that didn't meet at rest, on any body and however it is built. A thumb that brushes a thigh, under 1.5% of the body's height deep, or anything under a tenth of a second, doesn't show and isn't reported;
   - joints of a body built from parts that come apart (`joint_opens`);
   - hands through props.

   Set `LOOP=False` for clips that don't loop and `GROUND=None` for clips without ground contact.
2. **A filmstrip:** [render_views.py](../../scripts/render_views.py) with `VIEWS=["left"]` (and `"front"`), `FRAMES` every 3–4 frames of the cycle, `FLOOR=True`, `CLOSEUPS=[]`. The camera stays fixed, so a planted foot holds still against the floor across tiles. Look for:
   - feet planted flat at each contact, heel then toe;
   - knees and elbows bending the right way;
   - the arm opposite each leg swinging forward with it;
   - no hand crossing the body;
   - the hips rising and falling smoothly;
   - weight shifting over the standing foot.
3. **In the running game,** with the real movement code, as the engine's guide describes (Unity: `LocomotionTests`, `unity-dev:animation`).
4. Fix at the cause: the clip, its keys or the rig's weights here; the import settings, the speed values, the IK or the avatar in the engine.

## 5. Export

[export_fbx.py](../../scripts/export_fbx.py) with `ANIMATION=True`: no key reduction, the action's own frame range, one clip per file (`Character@Walk.fbx`).
