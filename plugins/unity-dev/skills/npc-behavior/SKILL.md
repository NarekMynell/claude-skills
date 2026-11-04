---
name: npc-behavior
description: Makes people and animals behave naturally in the game world - reasons behind actions, rest and activity, varied timing, smooth steering with no sliding, crowds that don't walk through each other, groups and queues, species behavior, and how to check it in the running game on a phone budget.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# NPC behavior

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

What people and animals do in the world, and how they move through it. The clips themselves come from the [animation](../animation/SKILL.md) guide; the code follows the [architecture](../code-standards/SKILL.md#architecture), with capabilities such as `IMovable`, and arrays with interfaces at the boundary for crowds ([capabilities](../code-standards/references/capabilities.md#thousands-of-objects-in-arrays)).

## Must

- **Every action has a visible reason:** hunger, tiredness, curiosity, a thing to look at. The player can guess why an actor does what it does. Random choice picks among sensible actions, it never replaces them.
- **Actors spend most of their time not walking.** Constant wandering reads as a machine. Each species and kind of person has an activity budget in `docs/`, and a long run of the behavior code, measured with `ActivityShares`, stays near it.
- **Movement looks like walking,** not like an arrow along a path: turns take time, speed changes take time, feet never slide, in the running game ([proof](../animation/SKILL.md#8-check)).
- **Actors don't walk through each other,** through walls or through props, at the densities the game really reaches.
- **The proof:** frame sequences of the real game from its camera, for the busiest scene the balance simulation predicts, with a written account of what is unnatural; `LocomotionTests` ([animation](../animation/SKILL.md#must)) at the real speeds; Play Mode tests at that density with [CrowdOverlapMeter and ActivityShares](../library/code/Core/Motion/README.md), and `FootSlideMeter` on a few actors inside the crowd, where avoidance shoves them, leaving their receipts (`crowd-*`, `locomotion-*`); the cost within budgets.

The methods below are a guide.

## What has failed

From a real project, in the owner's words: robotic, dry, lifeless, sliding, walking through each other.

- Actors moved at constant speed along straight segments, turning by interpolating their heading.
- Personal space was a visual offset added to positions: it shoved characters sideways with no step, which is sliding.
- Animals wandered between random points, all the time.

## Why they act

- **Needs and utility.** A few needs per kind (hunger, energy, fun, a purpose in the park), each rising over time, and actions scored by what they satisfy, through response curves: Dave Mark's utility approach. A dot product of a few weights is cheap enough for thousands of actors. Weights can come from hand tuning or offline training; a trained model that needs a runtime on the phone rarely pays for itself.
- **Time to commit.** Once chosen, an action runs until it ends or something important interrupts it. Re-deciding each frame makes actors twitch.
- **Reactions** are what make a world feel alive: a head turns toward a loud thing, a crowd looks at a firework, a child points at an animal, an animal flinches at a tap. Small, short, and caused by something the player can see.
- **A state machine or behavior tree per kind,** from the library's StateMachines module where it fits. New kinds are new classes behind the same interface, never a `switch` that grows ([example](../code-standards/references/capabilities.md#a-new-kind-without-touching-old-code)).

## Life in small things

Variety costs little, and a world without it looks copied.

- **No two alike at once:** random start phase, speed within about ±10%, choices weighted by personality. Nothing in sync, unless it's a marching band.
- **Idle isn't still.** Breathing, a shift of weight, a look around, an ear flick, a tail swish. Several idle variations, with holds of different lengths between them. Tiny motion can be in the shader, at no CPU cost.
- **Pauses.** People stop to look at a map, at a shop, at their phone. A walk has starts, stops and changes of mind.
- **Head first.** Eyes and head turn before the body. A character looks where it's going, and at what interests it.

## Animals

- **Activity budgets.** Animals rest far more than they move. Measured in zoos and studies: ring-tailed lemurs 48% resting, 19% moving, 16% feeding; an oncilla 66% resting, 21% moving, 3% feeding; lions about two thirds resting (figures from single studies, as a guide to proportions). Give each species a budget, and let it drive the choice of action.
- **Places, not points.** They go to water, food, shade, a favorite rock, the group; they don't wander to random coordinates. Planet Zoo 2's description of its animals is similar: routines such as exploring, resting and enrichment, with distractions such as joining a herd; players of the first game complained that its animals were almost always moving.
- **Each species has its own rhythm and character:** how it stands, how it moves ([gaits](../animation/references/motion-craft.md#four-legs)), what it does at rest, how it reacts to others. A herd keeps together and follows a leader; a cat is alone and still for a long time, then quick.
- **Groups.** Who is near whom matters: they rest together, one looks up and others follow.

## Steering

- **Limits, not interpolation.** Each actor has a maximum acceleration and a maximum turn rate. Speed changes through a ramp, and heading follows the velocity, or the velocity follows the heading for heavy animals. Start and stop clips, or a fade matched to the ramp, cover the changes ([no sliding](../animation/SKILL.md#4-locomotion-without-sliding)).
- **Smooth paths.** Cut corners with a look-ahead point, or curves, and slow down before sharp turns. A sharp turn at full speed is a slide.
- **Turning on the spot** needs stepping: a turn clip, or small steps. A character rotating with feet planted is sliding.
- **Paths are shared.** People keep to one side, slow down behind others, and don't all use the same line: a small lane offset per actor, chosen at the start of a segment, spreads a crowd with no extra cost.

## Crowds

Choose by the number of actors and the target device, and measure.

| Method | Good for | Cost and limits |
|---|---|---|
| Unity's NavMesh agents with avoidance | Tens of actors, varied terrain | Avoidance quality and priority are settings; lowering quality reduces cost with many agents. Gives Angular Speed and Acceleration directly |
| RVO2 / ORCA, in your own loop | Dense crowds that must avoid well | CPU per neighbor; check the license of the port you use (RVO2 is listed as Apache-2.0; some ports aren't for commercial use) |
| Steering plus a spatial grid in one system | Hundreds or more, simple avoidance, Web with one thread | Written for the game. Library: `SpatialHash<T>`. Neighbors change the actor's **desired velocity**, so it steers around them on its feet. It never pushes the position |
| Fewer near actors, simple far ones | Any crowd | Distance bands from `CullingGroup`: full behavior near, every Nth frame further, a looping path far, nothing off screen |

- **Order of solutions:** first spread them (lanes, staggered arrivals, wider paths where the simulation says crowds form), then avoid, and only then let small overlaps stay where nobody can see them.
- **Groups:** families and friends walk together. Research on real pedestrian groups found pairs walking side by side, triples in a V and larger groups in a U, and groups walking slower as they grow, slower still with children or the elderly ([Moussaïd et al. 2010](https://arxiv.org/abs/1003.3894)).
- **Queues:** each member waits behind the one ahead, with gaps that vary, shuffles forward with real steps, and looks around.

## Off screen

Behavior far away or off screen runs as cheap simulation or stops: nobody sees it. What matters when it returns is that the world looks like time passed. See [performance](../performance/SKILL.md#work-the-player-cant-see).

## Check

1. **Frame sequences from the running game,** from its camera, at the density the balance simulation predicts: a sequence of 8 to 12 frames over a few seconds shows sliding, popping and repetition that one screenshot can't.
2. **The questions:** Why is each of them doing that? Could I tell two of them apart? Does anything move in sync? Does anything slide, snap or pass through something? Is the scene alive when I do nothing?
3. **Numbers:** `FootSlideMeter` at every speed and `CrowdOverlapMeter` at peak density, in Play Mode tests; the behavior system's share of the frame.
4. A [fresh review](../standards/references/fresh-review.md) on the frame sequences.
