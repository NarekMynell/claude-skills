# Pacing

Turns a simulated player's timeline into pacing measures, and finds where the game breaks the promises the design states: dead zones, walls, repetition, dominant choices, overflow, runaway numbers. How to use it in a balance proof: the balance reference of `game-design:game-design`.

- **Destination:** `Pacing/`, its own assembly with no engine references, so a balance simulation in plain C# can use it from Edit Mode tests or outside Unity.
- **Depends on:** nothing. Its assembly stays free of the engine; a test assembly that references Core can write the receipt.

```csharp
var casual = new PacingTimeline("casual", totalSeconds: 8 * 3600);
// The simulation of the real game logic feeds it as the simulated player plays:
casual.Events.Add(new PacingEvent(12.0, PacingEventKind.Decision, "Burger Hut"));
casual.Events.Add(new PacingEvent(190.0, PacingEventKind.Unlock, "Second zone"));
casual.Samples.Add(new EconomySample(seconds: 60.0, money: 340.0, incomePerSecond: 4.5, nextGoalCost: 500.0));  // at least once a minute

var targets = new PacingTargets
{
    MinSimulatedSeconds = 8 * 3600,
    MinRuns = 20,
    MaxSecondsToFirstReward = 15,
    MaxSecondsBetweenDecisions = 120,
    MaxSecondsBetweenUnlocks = 600,
    MaxSecondsBetweenNovelty = 1200,
    MaxSameChoiceInARow = 5,
    MaxShareOfOneChoice = 0.3,
    MaxSecondsToNextGoal = 300,
    OverflowRatio = 5,
    MinOverflowSeconds = 120,
    MaxShownValue = 1e15,
    MaxIncomeGrowthPerHour = 20,
};
PacingReport report = PacingAnalyzer.AnalyzeRuns(new[] { casual }, targets);
ProofReceipt.Write("balance-casual", report.IsClean, report.ToString());
Assert.That(report.IsClean, report.ToString());
```

- **The targets are the design's, not the module's.** It has no defaults. Each is set, or listed in `targets.NotApplicable[name] = reason` for a game it doesn't fit; one left out is a `target-not-set` finding. Each number gets its reason in `docs/balance.md`.
- **One set of runs per kind of player:** active, casual, idle, free, spender, many runs each when rewards are random. `PacingAnalyzer.AnalyzeRuns` reports any finding from any run, with how many. `PacingAnalyzer.CompareMilestones` compares two kinds of player, so a free player's wall shows.
- **Labels are stable names.** Buying the same upgrade at a higher level uses the same label, or repetition stays invisible.
- **A proof that checks little can't pass:** too short a simulation, too few runs, no economy samples or holes in them over a minute are findings. The report prints the targets it held the game to, with what was excused and why.
- `Measures` holds the numbers to record in `docs/balance.md`, such as `decision_gap_p90_seconds` and `top_choice_share`.
