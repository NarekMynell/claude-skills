---
name: standards
description: Loads the game-design standards and guides - research, concepts, the game design document, production order, game feel, calculated balance and pacing, art direction - and turns game-design on for every session in the project. Add a task to start it right away; `off` and `on` switch every-session loading.
disable-model-invocation: true
argument-hint: "[task | on | off]"
allowed-tools:
  - Read(~/.claude/plugins/cache/*/game-design/**)
  - Read(~/.claude/plugins/cache/*/core/**)
---

# game-design standards

Game design for any engine, under the core standards. The engine's domain builds what these guides design, and its tools give some of the proofs (Unity: `unity-dev`).

## Musts

| Area | The bar | Proof, before the work counts as done | Guide |
|---|---|---|---|
| Balance | Calculated, every number justified; never boring, never a wall | A simulation of the real game logic per player type, from the first playable; a pacing analysis clean against targets stated first (Unity: `PacingAnalyzer`) | [balance](../game-design/references/balance.md) |
| Art | A current, beautiful look from references, one style throughout. One screen at final quality before mass production | `study_screenshot.py` on real game screenshots: no gaps against references; a written critique | [art direction](../art-direction/SKILL.md) |

## Verify before relying on them

The core rule holds. Market facts, store policies and the numbers these guides cite change: check what a decision rests on against current sources, and cite them in `docs/`.

Links here are relative to `${CLAUDE_SKILL_DIR}`.

## Guides

A whole game follows the [production order](../game-design/SKILL.md#production-order).

| Work | Guide |
|---|---|
| Game concepts, mechanics, features, the game design document | [game design](../game-design/SKILL.md) |
| Economy, progression, pacing | [balance](../game-design/references/balance.md) |
| Colors, style, the game's look | [art direction](../art-direction/SKILL.md) |
| A fresh review of the balance or the look | [reviews](references/reviews.md) |

## When the user types the command

Arguments: `$ARGUMENTS`

Every-session loading is `GAME_DESIGN_STANDARDS` under `env` in the project's `.claude/settings.json`, or in `.claude/settings.local.json`, which is personal and wins. unity-dev brings game-design with it. The core standards load with this command; their `core:skills` guide describes every switch and how to change it.

1. **`on` or `off`.** If the arguments are exactly `on` or `off`, set `GAME_DESIGN_STANDARDS` to that value as `core:skills` describes, with the read rules of game-design and core for `on`. Confirm in one line and stop.
2. **Every session.** If neither file sets `GAME_DESIGN_STANDARDS` and game-design isn't on in the project through another domain, set it to `on` as `core:skills` describes. Tell the user in one line that game-design now loads at the start of every session in this project, and that `/game-design:standards off` turns that off.
3. **Task.** The arguments are the task: start it. Without arguments, tell the user in one line that the standards are loaded, and wait.
