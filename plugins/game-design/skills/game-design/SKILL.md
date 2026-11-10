---
name: game-design
description: Game design process and quality bar for new games and features - market research, distinct concepts with a hook, the GDD, core and meta loops, proven balance and pacing, retention without dark patterns, production order from prototype to final quality, game feel.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/game-design/**)
---

# Game design

This guide can be wrong or out of date: verify what you rely on, as the [standards](../standards/SKILL.md#verify-before-relying-on-them) require.

**The bar:** a stranger who plays it would believe a passionate, talented team made it: nothing generic or placeholder left, nothing rushed, a world that is alive when you do nothing.

## Must

- **Think before deciding.** Each major decision (concept, core loop, economy, monetization) names the alternatives considered, why this one wins, and what would prove it wrong. Written in `docs/game-design.md`, so it can be checked later.
- **Balance and progression are calculated, justified and proven,** before they ship: targets first, a model, a simulation of the real game logic for each kind of player, every number with a reason, and no dead zone, wall, overflow or dominant choice in the report. It never bores the player, and never makes them wait with nothing to do. Method: [references/balance.md](references/balance.md).
- **Honest retention.** Retention is earned through fun, mastery and progression. No manipulative dark patterns. Young audiences get what the law and store policies require.
- **Self-critique at every milestone.** What would make a player quit here? What would bring them back tomorrow? Fix the answer before moving on. Then a [fresh review](../standards/references/reviews.md).

The rest is a guide.

## Research before design

Research the genre's current market on the web:

- the top games and why they succeed;
- what players praise and complain about in store reviews;
- audience preferences, monetization norms, platform policies.

Learn the principles; never copy a game, its content or its identity.

## Concepts

Propose several distinct concepts, each with its own hook: the one thing that makes it worth playing over the top games found in research. The user chooses when they are there to choose. When they asked you to decide, decide, and record why.

## Game design document

`docs/game-design.md` records:

- pillars and audience;
- the core loop, and the meta loop with its progression;
- session length and onboarding;
- retention mechanics and monetization;
- the decisions above, with their reasons.

Update it when the design changes.

## Production order

A whole game runs in this order, each step with its proof, and a fresh review at each milestone. Doing everything at once at low quality and polishing later means rebuilding it all.

1. **Research, concept, GDD.**
2. **The balance model and its targets** ([balance](references/balance.md)), before the content list exists: the content list comes from it.
3. **The architecture,** with its check in place before the first feature (Unity: the capability map in `docs/architecture.md` and `ProjectArchitectureTests`, `unity-dev:code-standards`).
4. **The core loop, playable,** with simple visuals, and the balance simulation running on it from now on. Fun is proven by playing, not by documents: have the user play it, when they are there.
5. **The vertical slice:** one scene or session at final quality. Art direction and its hero screen ([art direction](../art-direction/SKILL.md)), the UI concept, kit and key screen, a character and an animal walking and behaving in the game with their motion proven there, budgets set and measured. Everything is judged here, while changing it is cheap. For a Unity game the guides are `unity-dev:ui-quality`, `modeling:characters`, `modeling:animation` with `unity-dev:animation`, `unity-dev:npc-behavior` and `unity-dev:performance`.
6. **The content list** the slice implies: models, materials, sounds, effects and screens, each with its reuse (kits, variants, shared materials).
7. **Production,** each asset through its checks. Whoever builds, subagents included, is briefed with the guides and the bar.
8. **The whole game, again:** all the proofs on the final state, the balance simulation on the real content, all screens, a full session on a device, a fresh review of each area.

## Game feel

Every player action gets immediate feedback: motion, sound, VFX, haptics, camera. Tune the timing until it feels right.

Related, in Unity: `unity-dev:audio-design`, `unity-dev:vfx`, `unity-dev:ui-quality`.
