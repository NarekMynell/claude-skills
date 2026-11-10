---
name: animation
description: Plays character and animal animation in Unity without sliding - Humanoid import and retargeting, root motion settings, blend trees at measured speeds, foot IK for slopes and stairs, sockets and grips for held props, and Play Mode checks of foot sliding in the running game.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
argument-hint: "[character or motion]"
---

# Character animation in Unity

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

The clips come from `modeling:animation`, the character from `modeling:characters`, both imported as [models](../models/SKILL.md) describes. Unity setup and code: [references/unity-setup.md](references/unity-setup.md).

## Must

- **Natural in the running game.** Planted feet stay still and on the ground, at every speed the game uses. Speed fits the body. Weight, overlap and follow-through survive blending, IK and steering; nothing is robotic. Hands stay out of the body and out of props.
- **Checked in the game.** The project has a `LocomotionTests` Play Mode test per kind of mover (each human body, each animal gait) that runs the real movement code through [FootSlideMeter](../library/code/Core/Motion/README.md) at each speed it uses, and writes its receipt. A numeric check of the clip alone proves nothing about the game. Motion made in Unity, by code or in a shader, also passes the clip checks of `modeling:animation`: key or rebuild it on a Blender armature.
- **Known defects get fixed,** not deferred until someone sees them.

The method for each motion is a guide: your choice, inside this guide or outside it, for the best result in this project. Tell the user the choice and why, and record project-wide choices under **Decisions** in the project's `CLAUDE.md`. How actors move through the world and what they do is in the [NPC behavior](../npc-behavior/SKILL.md) guide.

**What has failed:** a project with clip speeds matched to the feet still pushed actors sideways in the game and deferred its worst slides, and its owner called the motion robotic and sliding. `modeling:animation` has the whole account.

**What works:** library clips retargeted through Humanoid; root motion or measured speeds against sliding; foot IK for the ground; sockets and grip poses for props.

**Sources** are `modeling:animation`'s, and two more for Unity projects only:

| Source | License | Notes |
|---|---|---|
| Unity Starter Assets: Third Person | Unity Companion License: Unity projects only | Humanoid idle, walk, run, jump |
| Kevin Iglesias, Basic Motions FREE | Unity Asset Store EULA: ship inside the game, don't redistribute | Humanoid basics |

## 1. Import

- **The character:** Animation Type Humanoid, Avatar Definition Create From This Model; check Configure Avatar as [models](../models/SKILL.md#rigs-and-avatars) describes.
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
- **Foot IK** on locomotion states pulls the feet back to where the clip had them, which corrects retargeting between different proportions. It doesn't fit the feet to the ground: section 3 does that.

## 2. Locomotion without sliding

Feet slide when the character moves at a different speed than the clip's feet. Sliding has more causes than a wrong number:

- **Speed:** the game's speed differs from the clip's, or the character's scale changed and the speed didn't.
- **Blends** between clips whose foot contacts don't line up.
- **Starts and stops:** full speed while a clip still fades in, or a stop with the walk still fading out.
- **Turning in place** with the feet still planted, and sharp turns at full speed.
- **Avoidance or crowding** that moves a character with no step of its own.

Two setups keep the feet planted:

- **Root motion:** the clip moves the character, through Apply Root Motion or an `OnAnimatorMove` that passes `deltaPosition` to the CharacterController. Feet can't slide; code steers by choosing and blending clips. Best for grounded, deliberate movement.
- **Code-driven speed, in-place clips:** for responsive controls. Each clip has a measured speed **on this character**: a root-motion clip's from `Animator.velocity` while it plays on the character (Humanoid root motion scales with the character's size); an in-place clip's from `stride_speed_mps` of `inspect_animation.py` (`modeling:animation`) on the character's rig. The blend tree's thresholds are those speeds in m/s, its parameter is the character's actual horizontal speed, and above the fastest clip the state's speed multiplier is actual speed ÷ that clip's speed. Don't use Homogeneous Speed on a speed blend tree: it makes every clip move at the same speed.

Clips blended together put their foot contacts at the same normalized times, for example the left foot down at 0 and the right at 0.5: shift them with Cycle Offset. Short transitions, turn clips or turn-in-place for sharp turns, and start and stop clips keep the feet planted outside the loops too. Code: [references/unity-setup.md](references/unity-setup.md#root-motion-and-speed).

- **Stay near the clip's own rate.** Playing a clip far from its speed makes feet patter or float: ±25% is a working default to check by eye. Beyond it, another clip, or another speed. `inspect_animation.py` with `GAME_SPEED` reports the rate.
- **Advanced:** distance matching drives a clip by the distance covered instead of time, and stride warping scales the stride to the speed (`StrideScale = locomotion speed / root motion speed`, in Unreal's docs); Unity has neither built in. Where a character's phase is driven by code, as with crowds, advancing it by distance gives the same result: `phase += distance / stride length`.
- **Crowds:** ramps, turn rates and avoidance on velocity, never on position: [NPC behavior](../npc-behavior/SKILL.md#steering).

## 3. Slopes and stairs

- **Stairs get an invisible ramp collider** for the CharacterController, on a layer the foot raycasts ignore: the capsule glides up instead of popping up each step. A CharacterController's `stepOffset` (0.1–0.4 m for a 2 m human) handles single curbs.
- **Foot IK puts each foot on the real surface.** In `OnAnimatorIK`, a raycast down from above each foot hits the real steps or slope, the IK goal moves there, weighted by a curve that is 1 while the foot is planted, and the body lowers by the larger drop so the lower foot reaches. Smooth the drop, and the camera's height, over time. Code: [references/unity-setup.md](references/unity-setup.md#feet-on-slopes-and-stairs).
- **Long staircases** get stair clips, up and down, matched to the step height, with Root Y not baked and based on Feet, plus the same foot IK.
- **Animation Rigging** (`com.unity.animation.rigging`, embedded in Unity 6.6 as a core package, 6.6.0) adds constraints after the Animator: Two Bone IK with an elbow or knee hint, Multi-Parent, Multi-Aim.

## 4. Hands and held props

- **Sockets:** a transform under each hand bone at the grip point, with the project's axis convention (`modeling:characters`). Each prop's origin is its grip point with the same axes (`modeling:models`), so holding it is `prop.SetParent(socket, false)`. With Optimize Game Objects on, list the socket in Extra Transforms to Expose.
- **Grip poses:** an override layer with an Avatar Mask that enables only the fingers (LeftFingers and RightFingers), playing the one-frame grip clip of each prop type, from a library or keyed in `modeling:animation`. Humanoid IK has no finger IK.
- **Two-handed props:** the second hand reaches a second grip transform on the prop, through `SetIKPosition` and `SetIKRotation` in `OnAnimatorIK`, or a Two Bone IK constraint with an elbow hint.
- **Fingers never enter the prop:** the handle fits the grip pose (`modeling:models`), and `inspect_animation.py` with `PROPS` reports `hand_through_prop` on the clip.
- **Hands cutting the body** after retargeting come from proportions that differ from the actor's. Fixes, in order:
  1. narrow the arm muscle ranges on the character's own avatar, never on the clips' avatars;
  2. Mixamo's Character Arm-Space before download;
  3. an additive layer that opens the arms;
  4. IK or Animation Rigging after the Animator.

## 5. Check in the game

**In Play Mode, with the real movement code:** `LocomotionTests` walks and runs each kind of mover at every speed, at the scale it really has. [FootSlideMeter and Gait](../library/code/Core/Motion/README.md) give both feet's slide per step against a limit from the leg's length, about 3 cm for a person, the speed against the body and the cadence. By eye: turns, starts and stops, a slope and the stairs. Capture frames from the game's camera and from the side, and check the speed (`Animator.velocity` against the controller's), the hands and the props.

Fix at the cause: the clip (`modeling:animation`), its import settings, the speed values, the IK, or the avatar's muscle limits.
