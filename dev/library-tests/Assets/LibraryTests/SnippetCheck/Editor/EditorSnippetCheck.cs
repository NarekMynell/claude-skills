// The snippets of Editor-only library modules and of the Pacing module, verbatim inside the smallest context that
// compiles them. A changed snippet is changed here too.
using System.Collections;
using NUnit.Framework;
using ProjectName.Core.Culling;
using ProjectName.Core.Editor.Architecture;
using ProjectName.Core.Editor.CostChecks;
using ProjectName.Core.Editor.UiChecks;
using ProjectName.Core.Motion;
using ProjectName.Core.Proofs;
using ProjectName.Pacing;
using Unity.Profiling;
using UnityEngine;
using UnityEngine.TestTools;

namespace LibraryTests.SnippetCheck.Editor
{
    internal sealed class ArchitectureSnippet
    {
        // Architecture README
        [Test, Explicit("A snippet: it audits a project that doesn't exist here.")]
        public void CodeFollowsTheArchitectureRules()
        {
            var options = new ArchitectureAuditOptions("StarHarbor")
                .Allow("mutable-static", "StarHarbor.Core.DI.GlobalResolver", "The one documented last-resort access point.");
            ArchitectureReport report = ArchitectureAudit.Run(options);
            ProofReceipt.Write("architecture", report.IsClean, report.ToString());
            Assert.That(report.IsClean, report.ToString());
        }
    }

    internal sealed class LocomotionSnippet
    {
        private interface IMovable
        {
            void MoveAtSpeed(Vector3 direction, float speed);
        }

        private static IMovable SpawnVisitor() => null;

        private static Animator AnimatorOf(IMovable mover) => null;

        // Motion README
        [UnityTest, Explicit("A snippet: its stubs return nothing.")]
        public IEnumerator Walking_LooksLikeWalking([Values(1.0f, 1.4f)] float speed)
        {
            IMovable mover = SpawnVisitor();    // through the game's own factory
            Animator animator = AnimatorOf(mover);
            mover.MoveAtSpeed(Vector3.forward, speed);
            yield return new WaitForSeconds(1f);  // past the start of the walk

            float leg = Gait.LegLength(animator);
            var left = new FootSlideMeter(leg);
            var right = new FootSlideMeter(leg);
            Transform leftFoot = animator.GetBoneTransform(HumanBodyBones.LeftFoot);
            Transform rightFoot = animator.GetBoneTransform(HumanBodyBones.RightFoot);
            var elapsed = 0f;
            while (elapsed < 4f)
            {
                left.Sample(leftFoot.position);
                right.Sample(rightFoot.position);
                elapsed += Time.deltaTime;
                yield return null;
            }

            float slide = Mathf.Max(left.WorstSlide, right.WorstSlide);
            float froude = Gait.Froude(speed, leg);
            float cadence = left.Steps / elapsed / Gait.ComfortableCyclesPerSecond(leg);
            bool passed = slide <= left.AllowedSlide && froude <= Gait.MaxWalkingFroude && cadence >= 0.5f && cadence <= 1.6f;
            ProofReceipt.Write($"locomotion-visitor-{speed}", passed, $"leg {leg:0.00} m, worst slide {slide:0.000} m, limit {left.AllowedSlide:0.000} m, Froude {froude:0.00}, cadence {cadence:0.00} of comfortable");
            Assert.That(passed, $"slide {slide}, Froude {froude}, cadence {cadence}");
        }

        public void Crowd(System.Collections.Generic.IReadOnlyList<Vector3> positions)
        {
            var overlaps = new CrowdOverlapMeter(minimumDistance: 0.5f);
            // Every frame:
            overlaps.Sample(positions, Time.deltaTime);
            // Afterwards, pairs closer than the minimum, per second:
            ProofReceipt.Write("crowd-peak", overlaps.PairsPerSecond < 1f, $"{overlaps.PairsPerSecond:0.00} overlapping pairs per second");
            Assert.That(overlaps.PairsPerSecond, Is.LessThan(1f));
        }
    }

    // stub: DOTween isn't in the test project.
    internal static class DOTween
    {
        public static int TotalPlayingTweens() => 0;
    }

    internal sealed class OffScreenSnippet
    {
        private readonly Camera gameCamera = null;
        private readonly int allowedTweens = 0;

        private readonly GameObject[] sceneRoots = new GameObject[0];
        private readonly int allowedMovers = 0;
        private readonly int budgetDrawCalls = 0;
        private readonly int budgetSetPassCalls = 0;
        private readonly int budgetTriangles = 0;

        // performance guide
        [UnityTest, Explicit("A snippet: its camera is a stub.")]
        public IEnumerator WithNothingInView_NothingWorks()
        {
            gameCamera.transform.rotation = Quaternion.LookRotation(Vector3.up);
            yield return new WaitForSeconds(0.5f);

            var probe = new MovementProbe(sceneRoots);
            yield return new WaitForSeconds(1f);

            int moved = probe.Moved().Count;
            int playing = DOTween.TotalPlayingTweens();
            bool passed = moved <= allowedMovers && playing <= allowedTweens;
            ProofReceipt.Write("off-screen-main", passed, $"{moved} renderers moved and {playing} tweens played with nothing in view; {allowedMovers} and {allowedTweens} allowed");
            Assert.That(passed, $"{moved} renderers moved, {playing} tweens played");
        }

        // performance guide
        [UnityTest, Explicit("A snippet: it needs the game's scene.")]
        public IEnumerator TheBusiestView_StaysInBudget()
        {
            using var drawCalls = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Draw Calls Count");
            using var setPasses = ProfilerRecorder.StartNew(ProfilerCategory.Render, "SetPass Calls Count");
            using var triangles = ProfilerRecorder.StartNew(ProfilerCategory.Render, "Triangles Count");
            yield return null;
            yield return null;

            bool passed = drawCalls.LastValue <= budgetDrawCalls && setPasses.LastValue <= budgetSetPassCalls && triangles.LastValue <= budgetTriangles;
            ProofReceipt.Write("budgets-main", passed, $"{drawCalls.LastValue} draw calls, {setPasses.LastValue} SetPass calls, {triangles.LastValue} triangles");
            Assert.That(passed, $"{drawCalls.LastValue} draw calls, {setPasses.LastValue} SetPass calls, {triangles.LastValue} triangles");
        }
    }

    internal sealed class CostSnippet
    {
        public void Audit(UnityEngine.SceneManagement.Scene scene)
        {
            // CostChecks README
            var options = new CostAuditOptions()
                .Allow("runtime-light", "Main/Sun", "The day cycle moves it: the look needs one realtime light.");
            SceneCostAudit.AuditLoadedScenes(receiptName: "main", options: options);

            var probe = new NeverMovedProbe(scene.GetRootGameObjects());
            // ... play the session ...
            foreach (CostFinding finding in probe.Report()) Debug.Log(finding);
        }
    }

    internal sealed class UiSnippet
    {
        public void Audit(RectTransform hudRoot)
        {
            // UiChecks README
            UiAudit.AuditAllCanvases(receiptName: "hud-20x9", noPanelOpen: true);
            UssTokenAudit.Run("Assets/_Project/UI", "tokens.uss", receiptName: "main");

            var options = new UiAuditOptions { MaxCoverage = 0.2f }
                .Allow("near-miss-alignment", "Hud/CoinBadge", "It overlaps its panel by design, for the sticker look.");
            UiAuditReport report = UiAudit.Run(hudRoot, options);
            Debug.Log(report);
        }
    }

    internal sealed class PacingSnippet
    {
        // Pacing README
        [Test]
        public void ReadmeExampleRuns()
        {
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
            Assert.That(report.IsClean, Is.False, "the example has long gaps on purpose: it only shows the calls");
        }
    }
}
