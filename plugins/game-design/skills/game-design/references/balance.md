# Balance and progression

This reference can be wrong or out of date: verify what you rely on, as the [standards](../../standards/SKILL.md#verify-before-relying-on-them) require.

A game's economy and pacing are designed like an engine: calculated, then tested. Think it through seriously: this decides whether players stay. Each number has a reason you could defend, and each claim has a simulation behind it. "It feels fine" isn't a reason, and neither is "it's what similar games do" without saying which and why it fits.

## The proof

`docs/balance.md` holds all of it, and the balance tests run with the other tests.

1. **Targets first,** before any formula, as promises to each kind of player: how soon the first reward comes, the longest wait between decisions, how often something new appears, how long the game lasts, the largest number the player ever sees. Sources rarely give these numbers, so they are your decisions: state each with its reason. Compare with similar games where you can measure them.
2. **The model.** Every formula and constant in one place, each constant with its reason.
3. **The simulation** runs the real game logic, not a copy of it: built from the same classes and registrations as the game, so it can't drift. It starts as soon as the core loop runs and goes on from there, with bots for at least these players: active, casual in short sessions, idle, free without ads, spender, many runs each.
4. **A pacing analyzer** (Unity: the code library's `PacingAnalyzer`, `unity-dev:library`) turns each player's runs into measures and findings against the targets, and the test fails on a finding, a target left unset, too short a simulation, too few runs or holes in the economy samples among them, and leaves its receipt (`balance-*`). A target that truly doesn't fit the game is waived with its reason, which the report prints. In Unity, copy the library's module.
5. **Sensitivity.** Move each main constant up and down 20% and rerun. A game that breaks with one number is balanced on luck: find out why. (The 20% is a working habit, not a sourced figure.)
6. **Against reality.** Playtest and compare real and simulated curves; correct the bots. Without players available, say so in the report: a simulation proves pacing, not fun.

## Boredom, measured

| What the player feels | What the simulation shows | Finding |
|---|---|---|
| Nothing to do but wait | No decision for a long stretch | `decision-gap`, `wall` |
| Nothing new | No unlock or new content for a long stretch | `unlock-gap`, `novelty-gap` |
| Same thing over and over | The same choice many times in a row | `repetition` |
| No real choice | One option wins nearly always | `dominant-choice` |
| Rich with nothing to buy | Money piles up, far beyond the next goal | `overflow` |
| Numbers mean nothing | Values beyond readable, such as $1.12e60, income growing out of hand | `runaway-number`, `runaway-income` |
| Punished for not paying | A free player reaches milestones far later, or never | `milestone-too-late`, `milestone-never-reached` |

Repeating an arc loses value quickly ([Daniel Cook on loops and arcs](https://lostgarden.com/2012/04/30/loops-and-arcs/)): ask of each stretch of the game what repeats and what doesn't, and give the loop something new at a rhythm. Transitions come on a slightly increasing curve, each a bit longer than the last, and big rewards aren't stacked at the same moment: too many close together dull each other, and long gaps make players think they are playing wrong ([Schreiber's pacing notes](https://gamedesignaspect.blogspot.com/2013/05)).

## Sessions

Mobile sessions are short and frequent. In GameAnalytics' 2024 data, the median session lasts about 5–6 minutes at about 4 sessions a day, simulation games about 4.2 minutes at 3.7 sessions, and D7 retention sits near 2–4% for most genres ([report](https://www.gameanalytics.com/reports/2025-mobile-gaming-benchmarks)). What follows from that, as inference: each session offers a meaningful decision within a minute or two, a visible goal reachable in this session, and a reason to return. Week one needs its own plan: most players are gone by day 7. Blog tables quoting much higher retention for idle games name no dataset: don't rely on them.

## Idle and tycoon math

From Anthony Pecorella's [The Math of Idle Games](https://www.gamedeveloper.com/design/the-math-of-idle-games-part-i) ([II](https://www.gamedeveloper.com/game-platforms/the-math-of-idle-games-part-ii), [III](https://www.gamedeveloper.com/design/the-math-of-idle-games-part-iii)):

- **Cost grows exponentially, production polynomially:** `cost = base × rate^owned`, `income = base × owned × multipliers`, so costs win eventually and the next tier takes over. AdVenture Capitalist's first generator: rate 1.07, base cost 4, 1.67 per second, x2 at 25 and 50 owned.
- **Buying n at once:** `base × rate^owned × (rate^n − 1) / (rate − 1)`. The most affordable: `floor(log_rate(money × (rate − 1) / (base × rate^owned) + 1))`.
- **The balancing measure is payback time:** cost ÷ added income. A bot buys the best ratio; plot income on a log scale, and tune multipliers so different generators lead at different stages. The same plot shows walls and runaway stretches.
- **Prestige** resets for a permanent multiplier: AdCap `150 × sqrt(lifetime / 1e15)`, Cookie Clicker `cbrt(lifetime / 1e12)`, Egg Inc `(run / 1e6)^0.14`. To double the prestige currency they need about 3–4x, 8x and 128x more earnings. A reset feels right when it gains about +50% to +200% of the current prestige currency ([Quest for Progress, GDC Europe 2016](https://www.slideshare.net/slideshow/quest-for-progress-gdc-europe-2016/65405507)).
- **Offline earnings** bring players back; Egg Inc's designer called its 2-hour cap a mistake that drove churn (same talk). Exponential growth gives a softer limit than a hard cap ([Idle Chatter, GDC 2016](https://www.slideshare.net/slideshow/idle-chatter-gdc-2016-59734260/59734260)).
- **Keep numbers readable,** as a design goal, not a display problem: letters up to the range your design states, and a bound on income at any day that the simulation enforces. Show time to afford alongside large prices.

For any genre: express prices in hours of play; draw the flow of each resource with its share ([handbook of a 150M-game designer](https://gamedeveloper.com/production/i-designed-economies-for-150m-games-here-s-my-ultimate-handbook)); keep the model closed.

## Faucets and sinks

Money per player rising over time means inflation, falling means deflation: balance sinks against faucets ([Schreiber](https://gamebalanceconcepts.wordpress.com/2010/09/08/level-10-final-boss/)). In the simulation, log income per hour against the target curve, the share of spending by currency, and the unspent stock. Every currency has a reason a player understands.

## Rewards, without dark patterns

- **Motivation that lasts** comes from competence, autonomy and relatedness (Self-Determination Theory; [Ryan, Rigby and Przybylski 2006](https://www.rochester.edu/news/printable.php?id=2719)) and from a difficulty that follows skill, between boredom and anxiety ([Chen on flow](https://khoury.northeastern.edu/~lieber/courses/csu670/f08/materials/p31-chen-flow-in-games.pdf)).
- **Near goals pull.** People speed up near a goal, and a head start helps: a card of 12 stamps with 2 given was finished faster than an empty card of 10 ([Kivetz et al. 2006](https://business.columbia.edu/faculty/research/goal-gradient-hypothesis-resurrected-purchase-acceleration-illusionary-goal)). Always show a goal close by, and a long one behind it.
- **Variable rewards** work when tied to something the player did, and are worth using only where the action is fun in itself ([Hopson](https://www.gamedeveloper.com/design/10-years-of-behavioral-game-design-with-bungie-s-research-boss)).
- **Limits:** real-money prices clear, odds disclosed before purchase ([Apple 3.1.1](https://developer.apple.com/app-store/review/guidelines/), [Google](https://support.google.com/googleplay/android-developer/answer/9858738)); for children, parental gates and restricted ads ([Apple 1.3](https://developer.apple.com/app-store/review/guidelines/), [Google Families](https://support.google.com/googleplay/android-developer/answer/12918983)). No confusing currencies or pressure on children ([EU consumer principles, 2025](https://connectontech.bakermckenzie.com/european-consumer-protection-network-issues-new-key-principles-on-in-game-virtual-currencies-impact-for-gaming-and-gambling-entities-in-belgium-the-eu-and-beyond/)).

## Monetization and balance

- A free player without ads must reach every milestone: state how much later a spender may be ahead, and test it by comparing their milestones (Unity: `PacingAnalyzer.CompareMilestones`).
- Rewarded ads are opt-in, offered at natural pauses, and add to the economy rather than replace it.
- Simulate the economy with and without each purchase: a purchase that removes a wall means the wall was built to sell it.

## In the report

Say what was simulated, for which players, with the numbers: first reward, longest waits, unlock and novelty gaps, highest values, sensitivity results. Say what no simulation can say: whether it is fun, until people play it.
