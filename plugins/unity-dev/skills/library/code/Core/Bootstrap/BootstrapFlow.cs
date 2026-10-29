using System;
using System.Collections.Generic;
using System.Threading;
using Company.Product.Core.Logging;
using Company.Product.Core.Providers;
using Cysharp.Threading.Tasks;
using UnityEngine;
using VContainer.Unity;

namespace Company.Product.Core.Bootstrap
{
    // Runs every registered IBootstrapStep in order and publishes the overall progress, so a loading
    // screen only subscribes to IProvider<BootstrapProgress>. A failing step stops the startup.
    public sealed class BootstrapFlow : IAsyncStartable
    {
        private readonly IReadOnlyList<IBootstrapStep> _steps;
        private readonly IProviderSetter<BootstrapProgress> _progress;

        public BootstrapFlow(IReadOnlyList<IBootstrapStep> steps, IProviderSetter<BootstrapProgress> progress)
        {
            _steps = steps ?? throw new ArgumentNullException(nameof(steps));
            _progress = progress ?? throw new ArgumentNullException(nameof(progress));
        }

        public async UniTask StartAsync(CancellationToken cancellation)
        {
            var count = _steps.Count;
            _progress.Set(new BootstrapProgress(BootstrapStatus.Running, 0f));
            for (var i = 0; i < count; i++)
            {
                // A step that ignores the token finishes normally after a shutdown; the next one must not start.
                if (cancellation.IsCancellationRequested) return;

                try
                {
                    await _steps[i].RunAsync(new StepProgress(_progress, i, count), cancellation);
                }
                // The scope's own shutdown, such as quitting during startup, ends it quietly: VContainer would
                // log a rethrown cancellation as an error.
                catch (OperationCanceledException) when (cancellation.IsCancellationRequested)
                {
                    return;
                }
                // Includes a step that cancelled itself, such as a timeout: that's a failure, not a shutdown.
                catch (Exception exception)
                {
                    Log.Exception(exception);
                    _progress.Set(new BootstrapProgress(BootstrapStatus.Failed, (float)i / count));
                    return;
                }

                if (i + 1 < count) _progress.Set(new BootstrapProgress(BootstrapStatus.Running, (float)(i + 1) / count));
            }

            _progress.Set(new BootstrapProgress(BootstrapStatus.Completed, 1f));
        }

        private sealed class StepProgress : IProgress<float>
        {
            private readonly IProviderSetter<BootstrapProgress> _progress;
            private readonly int _index;
            private readonly int _count;

            public StepProgress(IProviderSetter<BootstrapProgress> progress, int index, int count)
            {
                _progress = progress;
                _index = index;
                _count = count;
            }

            public void Report(float value) =>
                _progress.Set(new BootstrapProgress(BootstrapStatus.Running, (_index + Mathf.Clamp01(value)) / _count));
        }
    }
}
