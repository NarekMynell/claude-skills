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
| Architecture | code standards, capabilities | `docs/architecture.md`, the code, the receipt of `ProjectArchitectureTests` with its exceptions and signals. The test only says the floor holds: [what it can't see](#architecture) is this review's |
| Balance | game design, balance | `docs/balance.md`, the simulator, its reports per player type |
| Art | art direction, game assets | game screenshots at device size, references, `study_screenshot.py` sheets |
| Optimization | performance | budgets, receipts of `SceneCostAudit` and `OffScreenTests`, what each accepted exception costs |
| UI | UI quality, its review | device-size screenshots of every screen, `UiAudit` reports, references |
| Characters | characters, its review | contact sheets with the game camera, `inspect_character.py` reports |
| Motion | animation, NPC behavior | filmstrips, frame sequences from the running game, `inspect_animation.py` and `FootSlideMeter` numbers |

Then fix every real finding, and say what you dismissed and why. A finding is dismissed by evidence, never because fixing it is expensive.

## Architecture

A design is good when the next change is small, and no script can tell that. The agent answers, with file names:

1. **Walk three changes this game is likely to need,** from `docs/game-design.md`: a new kind of actor, a new rule, a new screen. Which existing files change? A new kind of thing that needs new `case`s in old `switch`es, or edits in more than one domain, is a defect.
2. **Are the interfaces capabilities?** Each is named for what it lets others do, and has more than one user or implementer, or a reason not to. One that copies one class's methods under its name is a defect the test can't fail: the receipt lists them.
3. **One job per class:** say each large class in one sentence with no "and". The receipt's signals point to the likely ones.
4. **Does anything know too much?** A domain that reads another's internals through a public type, a message that carries an object, a service that asks which kind of thing it holds.

For visual reviews, the agent has only images and numbers: make sure they show the game as it runs, from its own camera, at the size of a phone screen.
