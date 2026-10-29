---
name: game-design
description: Game design process and quality bar for new games and features - market research, distinct concepts with a hook, the GDD, core and meta loops, retention without dark patterns, core loop prototype first, game feel.
disable-model-invocation: true
allowed-tools:
  - Read(~/.claude/plugins/cache/*/unity-dev/**)
---

# Game design

**The bar:** the game feels made by a passionate, talented team. It is alive, emotional and polished, with nothing generic or placeholder left in the final product.

## Research before design

Research the genre's current market on the web:

- the top games and why they succeed;
- what players praise and complain about in store reviews;
- audience preferences, monetization norms, platform policies.

Learn the principles; never copy a game, its content or its identity.

## Concepts

Propose several distinct concepts, each with its own hook: the one thing that makes it worth playing over the top games found in research. The user chooses.

## Game design document

`docs/game-design.md` records:

- pillars and audience;
- the core loop, and the meta loop with its progression;
- session length and onboarding;
- retention mechanics and monetization.

Update it when the design changes.

## Principles

- **Retention is earned** through fun, mastery and progression. No manipulative dark patterns. For a young audience, follow the age-related laws and store policies on privacy, ads and purchases.
- **Prototype first.** Build the core loop early with simple visuals, and have the user play it before polishing. Fun is proven by playing, not by documents.
- **Game feel.** Every player action gets immediate feedback: motion, sound, VFX, haptics, camera. Tune the timing until it feels right.
- **Self-critique at every milestone.** What would make a player quit here? What would bring them back tomorrow? Fix the answer before moving on.

Related: [audio design](../audio-design/SKILL.md), [VFX](../vfx/SKILL.md), [UI quality](../ui-quality/SKILL.md).
