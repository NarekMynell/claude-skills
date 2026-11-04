using System;
using System.Collections.Generic;
using System.Linq;

namespace ProjectName.Pacing
{
    // Turns a simulated player's timeline into measures and finds where the game breaks its promises: dead zones, walls,
    // repetition, dominant choices, overflow, runaway numbers. It judges pacing, not fun: playtests still do that.
    public static class PacingAnalyzer
    {
        private const double SecondsPerHour = 3600d;
        private const double MaxSampleGapSeconds = 60d;

        public static PacingReport Analyze(PacingTimeline timeline, PacingTargets targets)
        {
            if (timeline == null) throw new ArgumentNullException(nameof(timeline));
            if (targets == null) throw new ArgumentNullException(nameof(targets));

            var findings = new List<PacingFinding>();
            var measures = new Dictionary<string, double>();
            CheckRequiredTargets(targets, findings);
            if (targets.MinSimulatedSeconds > 0d && timeline.TotalSeconds < targets.MinSimulatedSeconds)
                findings.Add(new PacingFinding("too-short", 0d, $"{timeline.TotalSeconds:0} s simulated, the game promises {targets.MinSimulatedSeconds:0} s"));
            var events = timeline.Events.OrderBy(e => e.Seconds).ToList();
            CheckFirstReward(events, targets, measures, findings);
            CheckGaps(events, PacingEventKind.Decision, "decision", targets.MaxSecondsBetweenDecisions, timeline.TotalSeconds, measures, findings);
            CheckGaps(events, PacingEventKind.Unlock, "unlock", targets.MaxSecondsBetweenUnlocks, timeline.TotalSeconds, measures, findings);
            CheckGaps(events, PacingEventKind.Novelty, "novelty", targets.MaxSecondsBetweenNovelty, timeline.TotalSeconds, measures, findings);
            CheckRepetition(events, targets, timeline.TotalSeconds, measures, findings);
            var samples = timeline.Samples.OrderBy(s => s.Seconds).ToList();
            CheckSamples(samples, timeline.TotalSeconds, targets, findings);
            CheckGoals(samples, targets, measures, findings);
            CheckOverflow(samples, targets, findings);
            CheckGrowth(samples, targets, measures, findings);
            return new PacingReport(timeline.Player, findings, measures, Describe(targets, 1));
        }

        // Many runs of one kind of player: a game with random rewards can pass on a lucky run. A finding from any run counts,
        // with how many runs it came from; each measure gives its median, and its worst value under the _worst name.
        public static PacingReport AnalyzeRuns(IReadOnlyCollection<PacingTimeline> runs, PacingTargets targets)
        {
            if (runs == null || runs.Count == 0) throw new ArgumentException("At least one run is needed.", nameof(runs));
            var reports = runs.Select(run => Analyze(run, targets)).ToList();
            var findings = new List<PacingFinding>();
            if (targets.MinRuns > 0 && runs.Count < targets.MinRuns)
                findings.Add(new PacingFinding("too-few-runs", 0d, $"{runs.Count} runs, the proof asks for {targets.MinRuns}"));
            foreach (var group in reports.SelectMany(r => r.Findings).GroupBy(f => f.Rule))
            {
                var first = group.First();
                var affected = reports.Count(r => r.Findings.Any(f => f.Rule == group.Key));
                findings.Add(new PacingFinding(group.Key, first.AtSeconds, $"in {affected} of {reports.Count} runs. First: {first.Detail}"));
            }

            var measures = new Dictionary<string, double>();
            foreach (var key in reports.SelectMany(r => r.Measures.Keys).Distinct().ToList())
            {
                var values = reports.Where(r => r.Measures.ContainsKey(key)).Select(r => r.Measures[key]).OrderBy(v => v).ToList();
                measures[key] = values[values.Count / 2];
                measures[key + "_worst"] = key.EndsWith("_per_hour", StringComparison.Ordinal) && !key.StartsWith("income", StringComparison.Ordinal) ? values[0] : values[values.Count - 1];
            }

            return new PacingReport(runs.First().Player, findings, measures, Describe(targets, runs.Count));
        }

        private static string Describe(PacingTargets targets, int runs)
        {
            var parts = new List<string> { $"runs {runs}" };
            void Add(string name, double value)
            {
                if (value > 0d) parts.Add($"{name} {value:0.##}");
            }

            Add(nameof(targets.MinSimulatedSeconds), targets.MinSimulatedSeconds);
            Add(nameof(targets.MinRuns), targets.MinRuns);
            Add(nameof(targets.MaxSecondsToFirstReward), targets.MaxSecondsToFirstReward);
            Add(nameof(targets.MaxSecondsBetweenDecisions), targets.MaxSecondsBetweenDecisions);
            Add(nameof(targets.MaxSecondsBetweenUnlocks), targets.MaxSecondsBetweenUnlocks);
            Add(nameof(targets.MaxSecondsBetweenNovelty), targets.MaxSecondsBetweenNovelty);
            Add(nameof(targets.MaxSameChoiceInARow), targets.MaxSameChoiceInARow);
            Add(nameof(targets.MaxShareOfOneChoice), targets.MaxShareOfOneChoice);
            Add(nameof(targets.MaxSecondsToNextGoal), targets.MaxSecondsToNextGoal);
            Add(nameof(targets.OverflowRatio), targets.OverflowRatio);
            Add(nameof(targets.MaxShownValue), targets.MaxShownValue);
            Add(nameof(targets.MaxIncomeGrowthPerHour), targets.MaxIncomeGrowthPerHour);
            parts.AddRange(targets.NotApplicable.Select(pair => $"{pair.Key} doesn't apply: {pair.Value}"));
            return string.Join("; ", parts);
        }

        // A money target with no money data, or with holes in it, checks nothing: a wall sampled only when it's over is no
        // wall. Samples come at a steady rate, whatever the player is doing.
        private static void CheckSamples(List<EconomySample> samples, double total, PacingTargets targets, List<PacingFinding> findings)
        {
            var usesMoney = targets.MaxSecondsToNextGoal > 0d || targets.OverflowRatio > 0d || targets.MaxShownValue > 0d || targets.MaxIncomeGrowthPerHour > 0d;
            if (!usesMoney) return;
            if (samples.Count == 0)
            {
                findings.Add(new PacingFinding("no-economy-samples", 0d, "the money targets have nothing to check: sample the economy at a steady rate, or say why they don't apply"));
                return;
            }

            var previous = 0d;
            foreach (var sample in samples)
            {
                if (sample.Seconds - previous > MaxSampleGapSeconds)
                {
                    findings.Add(new PacingFinding("sparse-samples", previous, $"{sample.Seconds - previous:0} s between economy samples, at most {MaxSampleGapSeconds:0} s: a wall can hide in there"));
                    return;
                }

                previous = sample.Seconds;
            }

            if (total - previous > MaxSampleGapSeconds)
                findings.Add(new PacingFinding("sparse-samples", previous, $"no economy samples for the last {total - previous:0} s"));
        }

        // The seconds a player takes to reach a milestone against another player's: a free player against a spender,
        // an idle player against an active one. Larger than the allowed ratio means a wall for that player.
        public static IReadOnlyList<PacingFinding> CompareMilestones(PacingTimeline baseline, PacingTimeline other, double maxRatio)
        {
            if (baseline == null) throw new ArgumentNullException(nameof(baseline));
            if (other == null) throw new ArgumentNullException(nameof(other));
            var findings = new List<PacingFinding>();
            var reached = FirstTimes(other);
            foreach (var milestone in FirstTimes(baseline))
            {
                if (!reached.TryGetValue(milestone.Key, out var seconds))
                    findings.Add(new PacingFinding("milestone-never-reached", milestone.Value, $"{other.Player} never reaches {milestone.Key}, which {baseline.Player} reaches"));
                else if (milestone.Value > 0d && seconds / milestone.Value > maxRatio)
                    findings.Add(new PacingFinding("milestone-too-late", seconds, $"{other.Player} reaches {milestone.Key} {seconds / milestone.Value:0.#} times later than {baseline.Player}, allowed {maxRatio:0.#}"));
            }

            return findings;
        }

        // Each target is a promise to the player. Leaving one out is how a dead zone or a wall goes unnoticed.
        private static void CheckRequiredTargets(PacingTargets targets, List<PacingFinding> findings)
        {
            Require(targets, targets.MinSimulatedSeconds, nameof(targets.MinSimulatedSeconds), findings);
            Require(targets, targets.MinRuns, nameof(targets.MinRuns), findings);
            Require(targets, targets.MaxSecondsToFirstReward, nameof(targets.MaxSecondsToFirstReward), findings);
            Require(targets, targets.MaxSecondsBetweenDecisions, nameof(targets.MaxSecondsBetweenDecisions), findings);
            Require(targets, targets.MaxSecondsBetweenUnlocks, nameof(targets.MaxSecondsBetweenUnlocks), findings);
            Require(targets, targets.MaxSecondsBetweenNovelty, nameof(targets.MaxSecondsBetweenNovelty), findings);
            Require(targets, targets.MaxSameChoiceInARow, nameof(targets.MaxSameChoiceInARow), findings);
            Require(targets, targets.MaxShareOfOneChoice, nameof(targets.MaxShareOfOneChoice), findings);
            Require(targets, targets.MaxSecondsToNextGoal, nameof(targets.MaxSecondsToNextGoal), findings);
            Require(targets, targets.OverflowRatio, nameof(targets.OverflowRatio), findings);
            Require(targets, targets.MaxShownValue, nameof(targets.MaxShownValue), findings);
            Require(targets, targets.MaxIncomeGrowthPerHour, nameof(targets.MaxIncomeGrowthPerHour), findings);
        }

        private static void Require(PacingTargets targets, double target, string name, List<PacingFinding> findings)
        {
            if (target > 0d) return;
            if (!targets.NotApplicable.TryGetValue(name, out var reason) || string.IsNullOrWhiteSpace(reason))
                findings.Add(new PacingFinding("target-not-set", 0d, $"{name} is a promise to this player: state it, or say why it doesn't apply"));
        }

        private static Dictionary<string, double> FirstTimes(PacingTimeline timeline)
        {
            var first = new Dictionary<string, double>();
            foreach (var item in timeline.Events.Where(e => e.Kind == PacingEventKind.Unlock || e.Kind == PacingEventKind.Novelty).OrderBy(e => e.Seconds))
                if (!first.ContainsKey(item.Label)) first.Add(item.Label, item.Seconds);
            return first;
        }

        private static void CheckFirstReward(List<PacingEvent> events, PacingTargets targets, Dictionary<string, double> measures, List<PacingFinding> findings)
        {
            var first = events.Where(e => e.Kind == PacingEventKind.Reward || e.Kind == PacingEventKind.Decision).Select(e => (double?)e.Seconds).FirstOrDefault();
            if (first == null)
            {
                findings.Add(new PacingFinding("no-first-reward", 0d, "the player never gets anything"));
                return;
            }

            measures["first_reward_seconds"] = first.Value;
            if (targets.MaxSecondsToFirstReward > 0d && first.Value > targets.MaxSecondsToFirstReward)
                findings.Add(new PacingFinding("late-first-reward", first.Value, $"{first.Value:0} s, target {targets.MaxSecondsToFirstReward:0} s"));
        }

        // The stretch after the last event counts too: a game that stops giving anything is the worst gap of all.
        private static void CheckGaps(List<PacingEvent> events, PacingEventKind kind, string name, double limit, double total, Dictionary<string, double> measures, List<PacingFinding> findings)
        {
            var times = events.Where(e => e.Kind == kind).Select(e => e.Seconds).ToList();
            if (times.Count == 0 && limit <= 0d) return;
            var gaps = new List<(double From, double Length)>();
            var previous = 0d;
            foreach (var time in times)
            {
                gaps.Add((previous, time - previous));
                previous = time;
            }

            gaps.Add((previous, total - previous));
            var lengths = gaps.Select(g => g.Length).OrderBy(l => l).ToList();
            measures[$"{name}_count_per_hour"] = times.Count / (total / SecondsPerHour);
            measures[$"{name}_gap_median_seconds"] = lengths[lengths.Count / 2];
            measures[$"{name}_gap_p90_seconds"] = lengths[(int)Math.Min(lengths.Count - 1, Math.Ceiling(lengths.Count * 0.9d) - 1)];
            measures[$"{name}_gap_longest_seconds"] = lengths[lengths.Count - 1];
            if (limit <= 0d) return;
            foreach (var gap in gaps.Where(g => g.Length > limit))
                findings.Add(new PacingFinding($"{name}-gap", gap.From, $"{gap.Length:0} s with no {name}, target {limit:0} s"));
        }

        private static void CheckRepetition(List<PacingEvent> events, PacingTargets targets, double total, Dictionary<string, double> measures, List<PacingFinding> findings)
        {
            var decisions = events.Where(e => e.Kind == PacingEventKind.Decision).ToList();
            if (decisions.Count == 0) return;
            var longest = 0;
            var streak = 0;
            string label = null;
            var streakStart = 0d;
            var worstStart = 0d;
            var worstLabel = string.Empty;
            foreach (var decision in decisions)
            {
                if (decision.Label == label)
                {
                    streak++;
                }
                else
                {
                    label = decision.Label;
                    streak = 1;
                    streakStart = decision.Seconds;
                }

                if (streak <= longest) continue;
                longest = streak;
                worstStart = streakStart;
                worstLabel = label;
            }

            measures["same_choice_longest_streak"] = longest;
            if (targets.MaxSameChoiceInARow > 0 && longest > targets.MaxSameChoiceInARow)
                findings.Add(new PacingFinding("repetition", worstStart, $"{worstLabel} {longest} times in a row, target {targets.MaxSameChoiceInARow}"));

            var top = decisions.GroupBy(d => d.Label).OrderByDescending(g => g.Count()).First();
            var share = top.Count() / (double)decisions.Count;
            measures["top_choice_share"] = share;
            measures["distinct_choices_per_hour"] = decisions.Select(d => d.Label).Distinct().Count() / (total / SecondsPerHour);
            if (targets.MaxShareOfOneChoice > 0d && share > targets.MaxShareOfOneChoice)
                findings.Add(new PacingFinding("dominant-choice", 0d, $"{top.Key} is {share * 100d:0}% of all decisions, target {targets.MaxShareOfOneChoice * 100d:0}%"));
        }

        private static void CheckGoals(List<EconomySample> samples, PacingTargets targets, Dictionary<string, double> measures, List<PacingFinding> findings)
        {
            var worst = 0d;
            var worstAt = 0d;
            var highest = 0d;
            var highestAt = 0d;
            foreach (var sample in samples)
            {
                var largest = Math.Max(Math.Max(sample.Money, sample.NextGoalCost), sample.IncomePerSecond);
                if (largest > highest)
                {
                    highest = largest;
                    highestAt = sample.Seconds;
                }

                if (sample.NextGoalCost <= sample.Money) continue;
                var seconds = sample.IncomePerSecond > 0d ? (sample.NextGoalCost - sample.Money) / sample.IncomePerSecond : double.PositiveInfinity;
                if (seconds <= worst) continue;
                worst = seconds;
                worstAt = sample.Seconds;
            }

            if (samples.Count == 0) return;
            measures["seconds_to_next_goal_worst"] = worst;
            measures["highest_value"] = highest;
            if (targets.MaxSecondsToNextGoal > 0d && worst > targets.MaxSecondsToNextGoal)
                findings.Add(new PacingFinding("wall", worstAt, double.IsPositiveInfinity(worst) ? "no income and a goal out of reach" : $"{worst:0} s to save for the next goal, target {targets.MaxSecondsToNextGoal:0} s"));
            if (targets.MaxShownValue > 0d && highest > targets.MaxShownValue)
                findings.Add(new PacingFinding("runaway-number", highestAt, $"a value of {highest:0.##e0} reaches the player, the design's limit is {targets.MaxShownValue:0.##e0}"));
        }

        private static void CheckOverflow(List<EconomySample> samples, PacingTargets targets, List<PacingFinding> findings)
        {
            if (targets.OverflowRatio <= 0d) return;
            var start = double.NaN;
            foreach (var sample in samples)
            {
                var overflowing = sample.NextGoalCost <= 0d || sample.Money > sample.NextGoalCost * targets.OverflowRatio;
                if (!overflowing)
                {
                    start = double.NaN;
                    continue;
                }

                if (double.IsNaN(start)) start = sample.Seconds;
                if (sample.Seconds - start < targets.MinOverflowSeconds) continue;
                findings.Add(new PacingFinding("overflow", start, $"money stays over {targets.OverflowRatio:0.#} times the next goal's price for {targets.MinOverflowSeconds:0} s: nothing left to want"));
                return;
            }
        }

        private static void CheckGrowth(List<EconomySample> samples, PacingTargets targets, Dictionary<string, double> measures, List<PacingFinding> findings)
        {
            var worst = 0d;
            var worstAt = 0d;
            for (var i = 0; i < samples.Count; i++)
            {
                if (samples[i].IncomePerSecond <= 0d) continue;
                for (var j = i + 1; j < samples.Count; j++)
                {
                    var elapsed = samples[j].Seconds - samples[i].Seconds;
                    if (elapsed < SecondsPerHour) continue;
                    var growth = Math.Pow(samples[j].IncomePerSecond / samples[i].IncomePerSecond, SecondsPerHour / elapsed);
                    if (growth > worst)
                    {
                        worst = growth;
                        worstAt = samples[i].Seconds;
                    }

                    break;
                }
            }

            if (worst <= 0d) return;
            measures["income_growth_per_hour_worst"] = worst;
            if (targets.MaxIncomeGrowthPerHour > 0d && worst > targets.MaxIncomeGrowthPerHour)
                findings.Add(new PacingFinding("runaway-income", worstAt, $"income grows {worst:0.#} times over in an hour, target {targets.MaxIncomeGrowthPerHour:0.#}"));
        }
    }
}
