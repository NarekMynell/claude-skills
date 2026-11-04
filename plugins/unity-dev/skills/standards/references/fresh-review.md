# Fresh review

This reference can be wrong or out of date: verify what you rely on, as the [standards](../SKILL.md#verify-before-relying-on-them) require.

Whoever built something judges it through what they meant it to be. A new agent sees what is there. A fresh review costs a fraction of what the user's rejection costs: run one at every milestone, and before reporting a whole game or a large feature as finished.

## How

Start a new agent, and give it the work, not your opinion of it. Its brief holds:

1. **The guide files to read,** by full path, for the area under review.
2. **What to look at:** the folders, the screenshots or sheets, and the receipts in `docs/proofs/`, with what changed since each.
3. **The question:** "Audit this against these guides. List every defect and every must without its proof, each with where it is and what it breaks. Say what the user would reject first. Don't fix anything."
4. **No conclusions from you.** Leave out what you think is good or what you already fixed.

| Milestone | The agent reads | It looks at |
|---|---|---|
| Architecture | code standards, capabilities | `docs/architecture.md`, the code, the receipt of `ProjectArchitectureTests` with its exceptions. Whether the interfaces are real capabilities, which no test can see |
| Balance | game design, balance | `docs/balance.md`, the simulator, its reports per player type |
| Art | art direction, game assets | game screenshots at device size, references, `study_screenshot.py` sheets |
| Optimization | performance | budgets, receipts of `SceneCostAudit` and `OffScreenTests`, what each accepted exception costs |
| UI | UI quality, its review | device-size screenshots of every screen, `UiAudit` reports, references |
| Characters | characters, its review | contact sheets with the game camera, `inspect_character.py` reports |
| Motion | animation, NPC behavior | filmstrips, frame sequences from the running game, `inspect_animation.py` and `FootSlideMeter` numbers |

Then fix every real finding, and say what you dismissed and why. A finding is dismissed by evidence, never because fixing it is expensive.

For visual reviews, the agent has only images and numbers: make sure they show the game as it runs, from its own camera, at the size of a phone screen.
