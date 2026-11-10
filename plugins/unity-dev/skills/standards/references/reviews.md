# Fresh reviews: Unity

This reference can be wrong or out of date: verify what you rely on, as the [standards](../SKILL.md#verify-before-relying-on-them) require.

The method, the brief and what the agent must not be told are core's (`core:standards`, its fresh review). These are this domain's milestones; game design and the models have theirs in their own domains.

| Milestone | The agent reads | It looks at |
|---|---|---|
| Architecture | code standards, capabilities | `docs/architecture.md`, the code, the receipt of `ProjectArchitectureTests` with its exceptions and signals. The test only says the floor holds: [what it can't see](#architecture) is this review's |
| Optimization | performance | budgets, receipts of `SceneCostAudit` and `OffScreenTests`, what each accepted exception costs |
| UI | UI quality, its review | device-size screenshots of every screen, `UiAudit` reports, references |
| Motion in the game | animation, NPC behavior | frame sequences from the running game, `FootSlideMeter` and `CrowdOverlapMeter` numbers |

## Architecture

A design is good when the next change is small, and no script can tell that. The agent answers, with file names:

1. **Walk three changes this game is likely to need,** from `docs/game-design.md`: a new kind of actor, a new rule, a new screen. Which existing files change? A new kind of thing that needs new `case`s in old `switch`es, or edits in more than one code domain, is a defect.
2. **Are the interfaces capabilities?** Each is named for what it lets others do, and has more than one user or implementer, or a reason not to. One that copies one class's methods under its name is a defect the test can't fail: the receipt lists them.
3. **One job per class:** say each large class in one sentence with no "and". The receipt's signals point to the likely ones.
4. **Does anything know too much?** A code domain that reads another's internals through a public type, a message that carries an object, a service that asks which kind of thing it holds.
