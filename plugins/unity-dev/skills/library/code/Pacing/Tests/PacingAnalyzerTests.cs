using System.Linq;
using NUnit.Framework;

namespace ProjectName.Pacing.Tests
{
    public sealed class PacingAnalyzerTests
    {
        private static string[] Rules(PacingReport report) => report.Findings.Select(f => f.Rule).ToArray();

        [Test]
        public void AGameThatKeepsItsPromises_IsClean()
        {
            var timeline = new PacingTimeline("casual", 600d);
            for (var t = 10; t < 600; t += 60)
                timeline.Events.Add(new PacingEvent(t, PacingEventKind.Decision, $"choice{t % 180}"));
            timeline.Events.Add(new PacingEvent(300d, PacingEventKind.Unlock, "zone2"));

            timeline.Events.Add(new PacingEvent(290d, PacingEventKind.Novelty, "shark"));
            for (var t = 0; t <= 600; t += 30) timeline.Samples.Add(new EconomySample(t, money: 10d + t, incomePerSecond: 1d, nextGoalCost: 40d + t));
            var report = PacingAnalyzer.Analyze(timeline, new PacingTargets
            {
                MinSimulatedSeconds = 600d,
                MinRuns = 1,
                MaxSecondsToFirstReward = 15d,
                MaxSecondsBetweenDecisions = 90d,
                MaxSecondsBetweenUnlocks = 400d,
                MaxSecondsBetweenNovelty = 400d,
                MaxSameChoiceInARow = 3,
                MaxShareOfOneChoice = 0.5d,
                MaxSecondsToNextGoal = 300d,
                OverflowRatio = 5d,
                MinOverflowSeconds = 60d,
                MaxShownValue = 1e9,
                MaxIncomeGrowthPerHour = 10d,
            });

            Assert.That(report.IsClean, report.ToString());
            Assert.That(report.Measures["decision_gap_longest_seconds"], Is.EqualTo(60d).Within(0.01d));
        }

        [Test]
        public void ALateFirstReward_IsReported()
        {
            var timeline = new PacingTimeline("new", 100d);
            timeline.Events.Add(new PacingEvent(40d, PacingEventKind.Reward, "coin"));

            Assert.That(Rules(PacingAnalyzer.Analyze(timeline, new PacingTargets { MaxSecondsToFirstReward = 15d })), Does.Contain("late-first-reward"));
        }

        [Test]
        public void NothingAtAll_IsReported()
        {
            Assert.That(Rules(PacingAnalyzer.Analyze(new PacingTimeline("new", 100d), new PacingTargets())), Does.Contain("no-first-reward"));
        }

        [Test]
        public void ADeadZone_IsReported_WhereItStarts()
        {
            var timeline = new PacingTimeline("casual", 1000d);
            timeline.Events.Add(new PacingEvent(10d, PacingEventKind.Decision, "a"));
            timeline.Events.Add(new PacingEvent(700d, PacingEventKind.Decision, "b"));
            timeline.Events.Add(new PacingEvent(990d, PacingEventKind.Decision, "c"));

            var gap = PacingAnalyzer.Analyze(timeline, new PacingTargets { MaxSecondsBetweenDecisions = 300d }).Findings.Single(f => f.Rule == "decision-gap");

            Assert.That(gap.AtSeconds, Is.EqualTo(10d));
        }

        [Test]
        public void TheStretchAfterTheLastEvent_CountsAsAGap()
        {
            var timeline = new PacingTimeline("late", 1000d);
            timeline.Events.Add(new PacingEvent(10d, PacingEventKind.Decision, "a"));

            Assert.That(Rules(PacingAnalyzer.Analyze(timeline, new PacingTargets { MaxSecondsBetweenDecisions = 300d })), Does.Contain("decision-gap"));
        }

        [Test]
        public void TheSameChoiceAgainAndAgain_IsRepetition_AndADominantChoice()
        {
            var timeline = new PacingTimeline("idle", 100d);
            for (var i = 0; i < 8; i++) timeline.Events.Add(new PacingEvent(i, PacingEventKind.Decision, "upgrade"));
            timeline.Events.Add(new PacingEvent(9d, PacingEventKind.Decision, "other"));

            var rules = Rules(PacingAnalyzer.Analyze(timeline, new PacingTargets { MaxSameChoiceInARow = 5, MaxShareOfOneChoice = 0.5d }));

            Assert.That(rules, Does.Contain("repetition"));
            Assert.That(rules, Does.Contain("dominant-choice"));
        }

        [Test]
        public void AGoalThatTakesTooLongToSaveFor_IsAWall()
        {
            var timeline = new PacingTimeline("casual", 100d);
            timeline.Events.Add(new PacingEvent(1d, PacingEventKind.Reward, "coin"));
            timeline.Samples.Add(new EconomySample(50d, money: 0d, incomePerSecond: 1d, nextGoalCost: 1000d));

            Assert.That(Rules(PacingAnalyzer.Analyze(timeline, new PacingTargets { MaxSecondsToNextGoal = 300d })), Does.Contain("wall"));
        }

        [Test]
        public void NoIncomeAndAGoalOutOfReach_IsAWall()
        {
            var timeline = new PacingTimeline("casual", 100d);
            timeline.Events.Add(new PacingEvent(1d, PacingEventKind.Reward, "coin"));
            timeline.Samples.Add(new EconomySample(50d, money: 0d, incomePerSecond: 0d, nextGoalCost: 10d));

            Assert.That(Rules(PacingAnalyzer.Analyze(timeline, new PacingTargets { MaxSecondsToNextGoal = 300d })), Does.Contain("wall"));
        }

        [Test]
        public void MoneyPilingUp_IsOverflow_OnlyWhenItLasts()
        {
            var timeline = new PacingTimeline("casual", 1000d);
            timeline.Events.Add(new PacingEvent(1d, PacingEventKind.Reward, "coin"));
            timeline.Samples.Add(new EconomySample(10d, money: 1000d, incomePerSecond: 1d, nextGoalCost: 10d));
            timeline.Samples.Add(new EconomySample(20d, money: 5d, incomePerSecond: 1d, nextGoalCost: 10d));
            var targets = new PacingTargets { OverflowRatio = 5d, MinOverflowSeconds = 60d };

            Assert.That(Rules(PacingAnalyzer.Analyze(timeline, targets)), Does.Not.Contain("overflow"));

            timeline.Samples.Add(new EconomySample(100d, money: 1000d, incomePerSecond: 1d, nextGoalCost: 10d));
            timeline.Samples.Add(new EconomySample(200d, money: 2000d, incomePerSecond: 1d, nextGoalCost: 10d));

            Assert.That(Rules(PacingAnalyzer.Analyze(timeline, targets)), Does.Contain("overflow"));
        }

        [Test]
        public void ANumberBeyondTheDesignsRange_IsReported()
        {
            var timeline = new PacingTimeline("whale", 100d);
            timeline.Events.Add(new PacingEvent(1d, PacingEventKind.Reward, "coin"));
            timeline.Samples.Add(new EconomySample(50d, money: 1.12e60, incomePerSecond: 1e50, nextGoalCost: 1d));

            Assert.That(Rules(PacingAnalyzer.Analyze(timeline, new PacingTargets { MaxShownValue = 1e15 })), Does.Contain("runaway-number"));
        }

        [Test]
        public void IncomeGrowingTooFast_IsReported()
        {
            var timeline = new PacingTimeline("active", 7200d);
            timeline.Events.Add(new PacingEvent(1d, PacingEventKind.Reward, "coin"));
            timeline.Samples.Add(new EconomySample(0d, 0d, incomePerSecond: 1d, nextGoalCost: 1d));
            timeline.Samples.Add(new EconomySample(3600d, 0d, incomePerSecond: 100d, nextGoalCost: 1d));

            Assert.That(Rules(PacingAnalyzer.Analyze(timeline, new PacingTargets { MaxIncomeGrowthPerHour = 10d })), Does.Contain("runaway-income"));
        }

        [Test]
        public void EveryTargetLeftOut_IsReported()
        {
            var timeline = new PacingTimeline("any", 1000d);
            timeline.Events.Add(new PacingEvent(1d, PacingEventKind.Decision, "a"));

            var report = PacingAnalyzer.Analyze(timeline, new PacingTargets());

            Assert.That(report.Findings.Count(f => f.Rule == "target-not-set"), Is.EqualTo(12));
        }

        [Test]
        public void ATargetThatDoesNotApply_NeedsAReason_AndIsNotReported()
        {
            var timeline = new PacingTimeline("any", 1000d);
            timeline.Events.Add(new PacingEvent(1d, PacingEventKind.Decision, "a"));

            var targets = new PacingTargets();
            targets.NotApplicable[nameof(PacingTargets.MaxShownValue)] = "No numbers grow in this game.";
            targets.NotApplicable[nameof(PacingTargets.OverflowRatio)] = " ";

            var report = PacingAnalyzer.Analyze(timeline, targets);

            Assert.That(report.Findings.Count(f => f.Rule == "target-not-set"), Is.EqualTo(11));
            Assert.That(report.ToString(), Does.Contain("No numbers grow in this game."));
        }

        [Test]
        public void ManyRuns_ReportAFindingFromAnyRun_WithHowMany()
        {
            var lucky = new PacingTimeline("casual", 100d);
            lucky.Events.Add(new PacingEvent(5d, PacingEventKind.Reward, "coin"));
            var unlucky = new PacingTimeline("casual", 100d);
            unlucky.Events.Add(new PacingEvent(50d, PacingEventKind.Reward, "coin"));

            var report = PacingAnalyzer.AnalyzeRuns(new[] { lucky, unlucky, lucky }, new PacingTargets { MaxSecondsToFirstReward = 15d });

            var finding = report.Findings.Single(f => f.Rule == "late-first-reward");
            Assert.That(finding.Detail, Does.Contain("in 1 of 3 runs"));
            Assert.That(report.Measures["first_reward_seconds"], Is.EqualTo(5d));
            Assert.That(report.Measures["first_reward_seconds_worst"], Is.EqualTo(50d));
        }

        [Test]
        public void TooShortASimulation_AndTooFewRuns_AreReported()
        {
            var run = new PacingTimeline("casual", 600d);
            var targets = new PacingTargets { MinSimulatedSeconds = 8 * 3600d, MinRuns = 20 };

            var rules = Rules(PacingAnalyzer.AnalyzeRuns(new[] { run }, targets));

            Assert.That(rules, Does.Contain("too-short"));
            Assert.That(rules, Does.Contain("too-few-runs"));
        }

        [Test]
        public void MoneyTargetsWithNoSamples_OrHolesInThem_AreReported()
        {
            var empty = new PacingTimeline("casual", 600d);
            var targets = new PacingTargets { MaxSecondsToNextGoal = 300d };
            Assert.That(Rules(PacingAnalyzer.Analyze(empty, targets)), Does.Contain("no-economy-samples"));

            var holes = new PacingTimeline("casual", 600d);
            holes.Samples.Add(new EconomySample(10d, 0d, 1d, 1d));
            holes.Samples.Add(new EconomySample(500d, 0d, 1d, 1d));
            Assert.That(Rules(PacingAnalyzer.Analyze(holes, targets)), Does.Contain("sparse-samples"));
        }

        [Test]
        public void APriceOrAnIncomeBeyondTheDesignsRange_IsReported()
        {
            var timeline = new PacingTimeline("whale", 100d);
            timeline.Samples.Add(new EconomySample(50d, money: 1d, incomePerSecond: 1d, nextGoalCost: 6.85e62));

            Assert.That(Rules(PacingAnalyzer.Analyze(timeline, new PacingTargets { MaxShownValue = 1e15 })), Does.Contain("runaway-number"));
        }

        [Test]
        public void NoRuns_AreRefused()
        {
            Assert.Throws<System.ArgumentException>(() => PacingAnalyzer.AnalyzeRuns(new PacingTimeline[0], new PacingTargets()));
        }

        [Test]
        public void AFreePlayerFarBehindASpender_IsReported_AndAMissingMilestoneToo()
        {
            var spender = new PacingTimeline("spender", 1000d);
            spender.Events.Add(new PacingEvent(100d, PacingEventKind.Unlock, "zone2"));
            spender.Events.Add(new PacingEvent(200d, PacingEventKind.Unlock, "zone3"));
            var free = new PacingTimeline("free", 1000d);
            free.Events.Add(new PacingEvent(900d, PacingEventKind.Unlock, "zone2"));

            var rules = PacingAnalyzer.CompareMilestones(spender, free, maxRatio: 3d).Select(f => f.Rule).ToArray();

            Assert.That(rules, Does.Contain("milestone-too-late"));
            Assert.That(rules, Does.Contain("milestone-never-reached"));
        }
    }
}
