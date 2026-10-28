using System;
using System.Threading;
using Cysharp.Threading.Tasks;
using UnityEngine;

namespace Company.Product.Core.Bootstrap
{
    // Mobile: no vSync and an explicit target, because the default renders at 30 fps.
    // Web: vSync, because targetFrameRate uses software timing there and micro-stutters.
    // Desktop: vSync.
    public sealed class FrameRateStep : IBootstrapStep
    {
        private readonly FrameRateConfig _config;

        public FrameRateStep(FrameRateConfig config) => _config = config != null ? config : throw new ArgumentNullException(nameof(config));

        public UniTask RunAsync(IProgress<float> progress, CancellationToken cancellationToken)
        {
            var (vSyncCount, targetFrameRate) = Resolve(
                Application.platform,
                Application.isMobilePlatform,
                _config.MobileFrameRate,
                _config.MatchDisplayRefreshRate,
                Screen.currentResolution.refreshRateRatio.value);

            QualitySettings.vSyncCount = vSyncCount;
            Application.targetFrameRate = targetFrameRate;
            progress?.Report(1f);
            return UniTask.CompletedTask;
        }

        internal static (int VSyncCount, int TargetFrameRate) Resolve(
            RuntimePlatform platform, bool isMobile, int mobileFrameRate, bool matchDisplayRefreshRate, double displayRefreshRate)
        {
            if (platform == RuntimePlatform.WebGLPlayer) return (1, -1);
            if (!isMobile) return (1, -1);

            var target = matchDisplayRefreshRate && displayRefreshRate > 0
                ? (int)Math.Round(displayRefreshRate)
                : mobileFrameRate;
            return (0, target);
        }
    }
}
