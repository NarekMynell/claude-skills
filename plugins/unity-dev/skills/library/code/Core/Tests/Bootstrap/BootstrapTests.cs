using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.Threading;
using Company.Product.Core.Bootstrap;
using Company.Product.Core.Providers;
using Cysharp.Threading.Tasks;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using Is = UnityEngine.TestTools.Constraints.Is;

namespace Company.Product.Core.Tests.Bootstrap
{
    public sealed class BootstrapTests
    {
        private sealed class Step : IBootstrapStep
        {
            private readonly List<string> _log;
            private readonly string _name;

            public Step(string name, List<string> log)
            {
                _name = name;
                _log = log;
            }

            public bool Fails { get; set; }

            public UniTask RunAsync(IProgress<float> progress, CancellationToken cancellationToken)
            {
                _log.Add(_name);
                progress.Report(0.5f);
                if (Fails) throw new InvalidOperationException($"{_name} failed");
                return UniTask.CompletedTask;
            }
        }

        [Test]
        public void Flow_RunsStepsInOrder_AndReportsOverallProgress()
        {
            var log = new List<string>();
            var progress = new Provider<BootstrapProgress>();
            var values = new List<float>();
            progress.Subscribe(state => values.Add(state.Value), notifyCurrentValue: false);
            var flow = new BootstrapFlow(new IBootstrapStep[] { new Step("a", log), new Step("b", log) }, progress);

            flow.StartAsync(CancellationToken.None).GetAwaiter().GetResult();

            Assert.That(log, Is.EqualTo(new[] { "a", "b" }));
            Assert.That(values, Is.EqualTo(new[] { 0f, 0.25f, 0.5f, 0.75f, 1f }));
            Assert.That(progress.Value.Status, Is.EqualTo(BootstrapStatus.Completed));
        }

        [Test]
        public void Flow_StopsAtAFailingStep_AndReportsFailure()
        {
            var log = new List<string>();
            var progress = new Provider<BootstrapProgress>();
            var steps = new IBootstrapStep[] { new Step("a", log) { Fails = true }, new Step("b", log) };

            LogAssert.Expect(LogType.Exception, new Regex("a failed"));
            new BootstrapFlow(steps, progress).StartAsync(CancellationToken.None).GetAwaiter().GetResult();

            Assert.That(log, Is.EqualTo(new[] { "a" }));
            Assert.That(progress.Value.Status, Is.EqualTo(BootstrapStatus.Failed));
        }

        [TestCase(RuntimePlatform.Android, true, 60, false, 120.0, 0, 60)]
        [TestCase(RuntimePlatform.IPhonePlayer, true, 60, true, 120.0, 0, 120)]
        [TestCase(RuntimePlatform.WebGLPlayer, false, 60, false, 60.0, 1, -1)]
        [TestCase(RuntimePlatform.WebGLPlayer, true, 60, true, 120.0, 1, -1)]
        [TestCase(RuntimePlatform.WindowsPlayer, false, 60, false, 144.0, 1, -1)]
        public void FrameRate_FollowsThePlatformRules(
            RuntimePlatform platform, bool isMobile, int mobileFrameRate, bool matchDisplay, double refreshRate, int vSync, int target)
        {
            Assert.That(FrameRateStep.Resolve(platform, isMobile, mobileFrameRate, matchDisplay, refreshRate), Is.EqualTo((vSync, target)));
        }
    }
}
