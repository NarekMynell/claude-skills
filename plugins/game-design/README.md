# game-design

Game design for any engine: research, concepts with a hook, the game design document, loops, production order, game feel, calculated balance and pacing, and art direction. The engine's domain builds what it designs; unity-dev brings it with it.

Switch: `GAME_DESIGN_STANDARDS`. Builds on core.

- `study_screenshot.py`, the art direction's check, runs in Blender, headless or through the Blender MCP connector. It is tested headless by `dev/run-blender-tests.sh`.

## Install

```text
/plugin install game-design --marketplace NarekMynell/claude-skills
```

## Skills

<!-- catalog:skills -->
| Skill | Command | What it does | Switch |
|---|---|---|---|
| [art-direction](skills/art-direction/SKILL.md) | `/game-design:art-direction` | Gives a game a current, beautiful look - references, palette and value plan, shape language, stylized light with no runtime cost, environment composition from the game camera, readable scale on a phone, one final-quality screen before production, screenshot studies against references. | `GAME_DESIGN_SKILL_ART_DIRECTION` |
| [game-design](skills/game-design/SKILL.md) | `/game-design:game-design` | Game design process and quality bar for new games and features - market research, distinct concepts with a hook, the GDD, core and meta loops, proven balance and pacing, retention without dark patterns, production order from prototype to final quality, game feel. | `GAME_DESIGN_SKILL_GAME_DESIGN` |
| [standards](skills/standards/SKILL.md) | `/game-design:standards` | Loads the game-design standards and guides - research, concepts, the game design document, production order, game feel, calculated balance and pacing, art direction - and turns game-design on for every session in the project. Add a task to start it right away; `off` and `on` switch every-session loading. | `GAME_DESIGN_STANDARDS` |
<!-- /catalog -->
