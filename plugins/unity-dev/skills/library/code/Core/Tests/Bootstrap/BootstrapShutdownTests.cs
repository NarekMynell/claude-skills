using System;
using System.Threading;
using Company.Product.Core.Bootstrap;
using Company.Product.Core.Providers;
using Cysharp.Threading.Tasks;
using NUnit.Framework;

namespace Company.Product.Core.Tests.Bootstrap
{
    public sealed class BootstrapShutdownTests
    {
        // Like a third-party SDK init or FrameRateStep: it doesn't observe the token.
        private sealed class TokenIgnoringStep : IBootstrapStep
        {
            public readonly UniTaskCompletionSource Gate = new UniTaskCompletionSource();

            public UniTask RunAsync(IProgress<float> progress, CancellationToken cancellationToken) => Gate.Task;
        }

        private sealed class RecordingStep : IBootstrapStep
        {
            public bool Ran { get; private set; }

            public UniTask RunAsync(IProgress<float> progress, CancellationToken cancellationToken)
            {
                Ran = true;
                return UniTask.CompletedTask;
            }
        }

        // README: "Only the scope's own shutdown counts as cancellation, and it ends the startup quietly".
        [Test]
        public void ShutdownDuringAStepThatIgnoresTheToken_EndsTheStartup()
        {
            var first = new TokenIgnoringStep();
            var next = new RecordingStep();
            var progress = new Provider<BootstrapProgress>();
            var flow = new BootstrapFlow(new IBootstrapStep[] { first, next }, progress);
            var shutdown = new CancellationTokenSource();

            var run = flow.StartAsync(shutdown.Token);
            shutdown.Cancel();
            first.Gate.TrySetResult();

            Assert.That(run.Status, Is.EqualTo(UniTaskStatus.Succeeded));
            Assert.That(next.Ran, Is.False, "A step ran after the scope shut down.");
            Assert.That(progress.Value.Status, Is.Not.EqualTo(BootstrapStatus.Completed), "The startup reported Completed after the shutdown.");
            shutdown.Dispose();
        }
    }
}
