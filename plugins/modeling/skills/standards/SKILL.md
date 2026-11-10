---
name: standards
description: Loads the modeling standards and guides - game-ready 3D models, environments and kits, characters and animals with rigs, animation clips, the Blender checks and contact sheets - and turns modeling on for every session in the project. Add a task to start it right away; `off` and `on` switch every-session loading.
disable-model-invocation: true
argument-hint: "[task | on | off]"
allowed-tools:
  - Read(~/.claude/plugins/cache/*/modeling/**)
  - Read(~/.claude/plugins/cache/*/core/**)
---

# modeling standards

3D models for games and real-time apps, built in Blender through the Blender MCP connector and judged by checks and renders, under the core standards. How an engine takes them in is its own domain's guide (Unity: `unity-dev:models`, `unity-dev:animation`).

## Musts

| Area | The bar | Proof, before the work counts as done | Guide |
|---|---|---|---|
| Models | No stacked or hidden faces, no artifacts, no visible facets on curves, no smeared or stretched texture | `validate_mesh.py` passes; contact-sheet critique finds nothing | [models](../models/SKILL.md) |
| Characters, animals | Nothing visibly pokes through anything: in any variant, in any pose, from the game's camera. However built | `inspect_character.py` over all variants; sheet with `GAME_VIEW` | [characters](../characters/SKILL.md) |
| Motion clips | Natural: speed fits the body; weight and overlap, nothing robotic; planted feet still | `inspect_animation.py` per clip; filmstrip reviewed | [animation](../animation/SKILL.md) |

## Verify before relying on them

The core rule holds. Blender's Python API and exporter options change between versions: check an operator or property in the connected Blender (`search_api_docs`, `get_python_api_docs`) before using it. Add-ons and asset sources: their own documentation, for the versions the user has.

## Scripts

The checks and tools are in `${CLAUDE_PLUGIN_ROOT}/scripts/`. [models](../models/SKILL.md#running-the-scripts) says how to run them.

Links here are relative to `${CLAUDE_SKILL_DIR}`.

## Guides

| Work | Guide |
|---|---|
| 3D models, props, environments, modular kits | [models](../models/SKILL.md), through the Blender MCP connector |
| Characters and animals | [characters](../characters/SKILL.md), after [models](../models/SKILL.md) |
| Animation clips: sources, keying, checks | [animation](../animation/SKILL.md) |
| A fresh review of models, characters or motion | [reviews](references/reviews.md) |

## When the user types the command

Arguments: `$ARGUMENTS`

Every-session loading is `MODELING_STANDARDS` under `env` in the project's `.claude/settings.json`, or in `.claude/settings.local.json`, which is personal and wins. unity-dev brings modeling with it. The core standards load with this command; their `core:skills` guide describes every switch and how to change it.

1. **`on` or `off`.** If the arguments are exactly `on` or `off`, set `MODELING_STANDARDS` to that value as `core:skills` describes, with the read rules of modeling and core for `on`. Confirm in one line and stop.
2. **Every session.** If neither file sets `MODELING_STANDARDS` and modeling isn't on in the project through another domain, set it to `on` as `core:skills` describes. Tell the user in one line that modeling now loads at the start of every session in this project, and that `/modeling:standards off` turns that off.
3. **Task.** The arguments are the task: start it. Without arguments, tell the user in one line that the standards are loaded, and wait.
