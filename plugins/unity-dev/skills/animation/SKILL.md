---
name: animation
description: Animates characters and animals for Unity - library clips retargeted through Humanoid, or natural motion keyed by code, speed that fits the body, no foot sliding in the running game, foot IK for slopes and stairs, sockets and grips for held props, and automated checks of foot contact, gaits, robotic motion, loops and penetration.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
argument-hint: "[character or motion]"
---

# Character animation

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

The character comes from the [characters](../characters/SKILL.md) guide; the scripts and the review loop from [game assets](../game-assets/SKILL.md). Unity setup and code: [references/unity-setup.md](references/unity-setup.md).

## Must

- **Natural.** Planted feet stay still and on the ground in the running game, at every speed the game uses. Speed fits the body. Weight, overlap and follow-through are there; nothing is robotic. Hands stay out of the body and out of props.
- **Checked on the rig and in the game.** Every clip passes `inspect_animation.py`; a filmstrip review finds nothing left; the project has a `LocomotionTests` Play Mode test per kind of mover (each human body, each animal gait) that runs the real movement code through [FootSlideMeter](../library/code/Core/Motion/README.md) at each speed it uses, and writes its receipt. Motion on a custom pipeline or in a shader passes the same checks ([how](references/motion-craft.md#how-to-key-it)). A numeric check of the clip alone proves nothing about the game.
- **Known defects get fixed,** not deferred until someone sees them.

The method for each motion is a guide: your choice, inside this guide or outside it, for the best result in this project. Tell the user the choice and why, and record project-wide choices under **Decisions** in the project's `CLAUDE.md`. How actors move through the world and what they do is in the [NPC behavior](../npc-behavior/SKILL.md) guide.

**What has failed, twice.** Human motion keyed by code came out robotic, with sliding or floating feet and hands through the body. Then a project built skeleton motion for people and animals in code, with a good pipeline and clip speeds matched to the feet, and its owner still called it robotic, dry and sliding: it had checked only its clips' numbers, deferred the worst slides, had no weight or overlap, and pushed actors sideways in the game.

**What works:** motion capture or professional libraries retargeted through Humanoid where they exist, for people; for animals and for cartoon proportions, libraries where they fit ([sources](#2-sources)), or motion keyed with the [motion craft](references/motion-craft.md) rules; root motion or measured speeds against sliding; foot IK for the ground; sockets and grip poses for props.

## 1. Plan the clips

List every clip the game needs before getting any: idle; walk and run at their speeds; turns; jump start, loop and landing; stairs up and down if the levels have stairs; interactions such as pick up, open, hold and throw; hit and death. For each one record in `docs/art-direction.md`:

- whether it loops;
- root motion or in place, as [section 4](#4-locomotion-without-sliding) decides;
- the speed it moves at;
- the props it uses.

## 2. Sources

| Source | License | Notes |
|---|---|---|
| Quaternius Ultimate Animated Animal Pack | CC0 | 12 animals with more than 12 animations each, walk and gallop among them; the user downloads. Check what's rigged |
| Kenney Animated Characters | CC0 | Humans; check the animations |
| Truebones Zoo | Free, royalty-free for commercial use by its Gumroad page, no redistribution of the files, credit asked; read the terms before use | Over 75 animated animals, FBX |
| Mixamo | Free with an Adobe ID; royalty-free in games; the files can't be redistributed | The user downloads in the browser. FBX for Unity, Without Skin, 30 fps, keyframe reduction off; In Place for clips the code moves |
| Quaternius Universal Animation Library 1 and 2 | QAL v1.0: commercial use, no redistribution of the files ([details](../characters/references/sources.md#quaternius-stylized-humans-and-animation)) | Root-motion and in-place versions; the user downloads |
| Unity Starter Assets: Third Person | Unity Companion License: Unity projects only | Humanoid idle, walk, run, jump |
| Kevin Iglesias, Basic Motions FREE | Unity Asset Store EULA: ship inside the game, don't redistribute | Humanoid basics |
| CMU motion capture | Commercial use allowed, no resale, even converted | BVH, imported into Blender; avoid the 4TU FBX conversion, which is CC BY-NC |

Downloads are the user's: list the clips the game needs and ask for them at the start of the work, before the user goes away. For humans especially, keying by code is the method that has failed twice. When a brief forbids third-party content, or nothing can be downloaded, key with the [motion craft](references/motion-craft.md) rules, to the same bar, and report such motion as unproven until the user has seen it moving: send them a capture, and name it as the first thing to judge. Record every clip in `docs/third-party-assets.md`. Mixamo's Character Arm-Space setting widens the arms before download, for bulky characters whose arms would cut the body.

## 3. Import in Unity

- **The character:** Animation Type Humanoid, Avatar Definition Create From This Model; check Configure Avatar as the [characters guide](../characters/SKILL.md#6-export-and-check-in-unity) describes.
- **Clips:** Humanoid. Avatar Definition Copy From Other Avatar when the clip's skeleton is the character's own, as with Mixamo clips downloaded for the same character; otherwise Create From This Model, so Unity maps the clip's own skeleton and retargets between the two avatars.
- **Root motion settings** for each clip, on the Animation tab:

  | Clip | Root Rotation | Root Y | Root XZ |
  |---|---|---|---|
  | Idle, in-place loop | Bake Into Pose | Bake Into Pose | Bake Into Pose |
  | Straight walk or run with root motion | Bake Into Pose, Body Orientation | Bake Into Pose, Feet | Not baked: it moves the character |
  | Turn, curve, strafe | Not baked | Bake Into Pose, Feet | Not baked |
  | Jump, stairs, climb | Rotation baked if the facing doesn't change | Not baked, Based Upon Feet | Not baked |

  Bake rotation only where the clip starts and ends facing the same way, and adjust its Offset until the average velocity's X reads 0. Body Orientation misreads strafes: correct them with Offset, or base them on Original.
- **Loops:** Loop Time and Loop Pose for cycles. The loop-match lights should be green for rotation and Y; XZ needn't match. Mirror makes the other side's version of a clip.
- **Foot IK** on locomotion states pulls the feet back to where the clip had them, which corrects retargeting between different proportions. It doesn't fit the feet to the ground: section 5 does that.

## 4. Locomotion without sliding

Feet slide when the character moves at a different speed than the clip's feet. Sliding has more causes than a wrong number:

- **Speed:** the game's speed differs from the clip's, or the character's scale changed and the speed didn't.
- **Blends** between clips whose foot contacts don't line up.
- **Starts and stops:** full speed while a clip still fades in, or a stop with the walk still fading out.
- **Turning in place** with the feet still planted, and sharp turns at full speed.
- **Avoidance or crowding** that moves a character with no step of its own.

Two setups keep the feet planted:

- **Root motion:** the clip moves the character, through Apply Root Motion or an `OnAnimatorMove` that passes `deltaPosition` to the CharacterController. Feet can't slide; code steers by choosing and blending clips. Best for grounded, deliberate movement.
- **Code-driven speed, in-place clips:** for responsive controls. Each clip has a measured speed **on this character**: a root-motion clip's from `Animator.velocity` while it plays on the character (Humanoid root motion scales with the character's size); an in-place clip's from `stride_speed_mps` of `inspect_animation.py` on the character's rig. The blend tree's thresholds are those speeds in m/s, its parameter is the character's actual horizontal speed, and above the fastest clip the state's speed multiplier is actual speed ÷ that clip's speed. Don't use Homogeneous Speed on a speed blend tree: it makes every clip move at the same speed.

Clips blended together put their foot contacts at the same normalized times, for example the left foot down at 0 and the right at 0.5: shift them with Cycle Offset. Short transitions, turn clips or turn-in-place for sharp turns, and start and stop clips keep the feet planted outside the loops too. Code: [references/unity-setup.md](references/unity-setup.md#root-motion-and-speed).

- **Stay near the clip's own rate.** Playing a clip far from its speed makes feet patter or float: ±25% is a working default to check by eye. Beyond it, another clip, or another speed. `inspect_animation.py` with `GAME_SPEED` reports the rate.
- **Advanced:** distance matching drives a clip by the distance covered instead of time, and stride warping scales the stride to the speed (`StrideScale = locomotion speed / root motion speed`, in Unreal's docs); Unity has neither built in. Where a character's phase is driven by code, as with crowds, advancing it by distance gives the same result: `phase += distance / stride length`.
- **Crowds:** ramps, turn rates and avoidance on velocity, never on position: [NPC behavior](../npc-behavior/SKILL.md#steering).

## 5. Slopes and stairs

- **Stairs get an invisible ramp collider** for the CharacterController, on a layer the foot raycasts ignore: the capsule glides up instead of popping up each step. A CharacterController's `stepOffset` (0.1–0.4 m for a 2 m human) handles single curbs.
- **Foot IK puts each foot on the real surface.** In `OnAnimatorIK`, a raycast down from above each foot hits the real steps or slope, the IK goal moves there, weighted by a curve that is 1 while the foot is planted, and the body lowers by the larger drop so the lower foot reaches. Smooth the drop, and the camera's height, over time. Code: [references/unity-setup.md](references/unity-setup.md#feet-on-slopes-and-stairs).
- **Long staircases** get stair clips, up and down, matched to the step height, with Root Y not baked and based on Feet, plus the same foot IK.
- **Animation Rigging** (`com.unity.animation.rigging`, embedded in Unity 6.6 as a core package, 6.6.0) adds constraints after the Animator: Two Bone IK with an elbow or knee hint, Multi-Parent, Multi-Aim.

## 6. Hands and held props

- **Sockets:** an empty under the hand bone at the grip point, one per hand, with one orientation convention for the project, recorded in `docs/art-direction.md`. Each prop's origin is its grip point with the same axes, so holding it is `prop.SetParent(socket, false)`. With Optimize Game Objects on, list the socket in Extra Transforms to Expose.
- **Grip poses:** an override layer with an Avatar Mask that enables only the fingers (LeftFingers and RightFingers), playing a one-frame grip clip per prop type: from the library, or keyed on the character's rig in Blender with the fingers closed around the handle. Humanoid IK has no finger IK.
- **Two-handed props:** the second hand reaches a second grip transform on the prop, through `SetIKPosition` and `SetIKRotation` in `OnAnimatorIK`, or a Two Bone IK constraint with an elbow hint.
- **Fingers never enter the prop:** the handle's thickness fits the grip pose, about 3–4 cm for a full grip on a human hand. `inspect_animation.py` with `PROPS` reports `hand_through_prop`.
- **Hands cutting the body** after retargeting come from proportions that differ from the actor's. Fixes, in order:
  1. narrow the arm muscle ranges on the character's own avatar, never on the clips' avatars;
  2. Mixamo's Character Arm-Space before download;
  3. an additive layer that opens the arms;
  4. IK or Animation Rigging after the Animator.

## 7. Keying in Blender

For what is keyed by hand: block the key poses (contacts and extremes), then the breakdowns; arcs, ease in and out, and overlapping motion for secondary parts. Keep planted feet still in world space (IK, or Copy Global Transform, a Blender core feature since 5.0), and contacts on whole frames. Edits to library clips happen on the clip's own rig, at its own frame rate. Export with [export_fbx.py](../game-assets/scripts/export_fbx.py) and `ANIMATION=True`: no key reduction, the action's own frame range, one clip per file (`Character@Walk.fbx`).

## 8. Check

1. **Every clip in Blender, on the character's rig:** [inspect_animation.py](../game-assets/scripts/inspect_animation.py) reports:
   - planted feet that slide, feet below the ground or never reaching it;
   - for in-place clips, the speed the character must move at (`stride_speed_mps`) and the direction (`move_direction`);
   - the speed against the body (`froude`, `natural_walk_speed_mps`, `too_fast_for_a_walk`) and against the game (`GAME_SPEED`, `playback_rate_out_of_range`);
   - steps out of rhythm, and on four legs the gait and footfall order (`FEET`, `GAIT`, `wrong_gait`, `irregular_footfall`);
   - clips where no foot could be measured (`feet_not_measured`): hair and bags don't count as the body, and `BODY` settles it;
   - robotic motion: `no_pelvis_motion`, `trunk_still`, `stiff_knees`, `arms_hang_still`, `linear_motion`, `everything_moves_together`, `secondary_still`, `frozen`. `NATURAL=False` turns these off for machines;
   - arms swinging with the same-side leg;
   - loop seams and joint pops;
   - what the clip brings through what (`limbs_through_body`): surfaces with no joint between them, such as a hand in a hip or legs through each other, and layers on the same bones that didn't meet at rest, on any body and however it is built;
   - joints of a body built from parts that come apart (`joint_opens`);
   - hands through props.

   Set `LOOP=False` for clips that don't loop and `GROUND=None` for clips without ground contact.
2. **A filmstrip:** [render_views.py](../game-assets/scripts/render_views.py) with `VIEWS=["left"]` (and `"front"`), `FRAMES` every 3–4 frames of the cycle, `FLOOR=True`, `CLOSEUPS=[]`. The camera stays fixed, so a planted foot holds still against the floor across tiles. Look for:
   - feet planted flat at each contact, heel then toe;
   - knees and elbows bending the right way;
   - the arm opposite each leg swinging forward with it;
   - no hand crossing the body;
   - the hips rising and falling smoothly;
   - weight shifting over the standing foot.
3. **In Unity, in Play Mode, with the real movement code:** `LocomotionTests` walks and runs each kind of mover at every speed, at the scale it really has. [FootSlideMeter and Gait](../library/code/Core/Motion/README.md) give both feet's slide per step against a limit from the leg's length, about 3 cm for a person, the speed against the body and the cadence. By eye: turns, starts and stops, a slope and the stairs. Capture frames from the game's camera and from the side, and check the speed (`Animator.velocity` against the controller's), the hands and the props.
4. Fix at the cause: the clip, its import settings, the speed values, the IK, or the avatar's muscle limits.
