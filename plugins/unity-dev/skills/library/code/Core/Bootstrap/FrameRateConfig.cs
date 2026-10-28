using UnityEngine;

namespace Company.Product.Core.Bootstrap
{
    [CreateAssetMenu(menuName = "Company.Product/Core/Frame Rate Config", fileName = "FrameRateConfig")]
    public sealed class FrameRateConfig : ScriptableObject
    {
        [Tooltip("Target on Android and iOS. Unity's default there is a fixed 30 fps.")]
        [SerializeField, Min(30)] private int _mobileFrameRate = 60;

        [Tooltip("Use the display's refresh rate on mobile instead, for games designed for high-refresh screens.")]
        [SerializeField] private bool _matchDisplayRefreshRate;

        public int MobileFrameRate => _mobileFrameRate;

        public bool MatchDisplayRefreshRate => _matchDisplayRefreshRate;
    }
}
