# modeling

3D models for games and real-time apps, built in Blender through the Blender MCP connector: models, environments and modular kits, characters and animals with rigs, animation clips. Every result passes automated checks and a contact-sheet review before it counts. How an engine takes the models in is that engine's domain (Unity: `unity-dev:models`); unity-dev brings modeling with it.

Switch: `MODELING_STANDARDS`. Builds on core. Requires Blender with the Blender MCP connector.

The checks and tools are in [scripts/](scripts/): mesh validation, contact sheets with the game camera, skeleton-first bodies, character checks for every way of building a body, cutting what stays hidden, animation checks for any number of legs and for robotic motion, light baking and gated FBX export. They are tested headless against scenes with known defects and clean scenes built each way (`dev/run-blender-tests.sh`, `dev/run-attack-tests.sh`), and against the professional models and clips inside a Unity install (`dev/run-real-assets.sh`).

## Install

```text
/plugin install modeling --marketplace NarekMynell/claude-skills
```

## Skills

<!-- catalog:skills -->
| Skill | Command | What it does | Switch |
|---|---|---|---|
| [animation](skills/animation/SKILL.md) | `/modeling:animation` | Makes natural animation clips in Blender for characters and animals - the clip plan, library sources, motion keyed by the craft's rules when nothing fits, automated checks of foot contact, speed, gaits, robotic motion, loops and penetration, filmstrip reviews, and export. | `MODELING_SKILL_ANIMATION` |
| [characters](skills/characters/SKILL.md) | `/modeling:characters` | Creates the project's own game-ready characters and animals in Blender - transformed professional bases or skeleton-first bodies built from scratch, single-layer clothes and hair, variants that fit each other, humanoid rigging and skinning, and automated anatomy, penetration, weight and deformation checks with reviews from the game's camera. | `MODELING_SKILL_CHARACTERS` |
| [models](skills/models/SKILL.md) | `/modeling:models` | Creates game-ready 3D models and environments in Blender through the Blender MCP connector - asset planning and reuse, modular kits, clean geometry, automated checks, contact-sheet reviews, UVs, textures and materials, LODs, collision meshes, and gated export. | `MODELING_SKILL_MODELS` |
| [standards](skills/standards/SKILL.md) | `/modeling:standards` | Loads the modeling standards and guides - game-ready 3D models, environments and kits, characters and animals with rigs, animation clips, the Blender checks and contact sheets - and turns modeling on for every session in the project. Add a task to start it right away; `off` and `on` switch every-session loading. | `MODELING_STANDARDS` |
<!-- /catalog -->
