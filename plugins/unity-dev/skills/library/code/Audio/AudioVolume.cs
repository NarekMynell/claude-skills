using UnityEngine;

namespace Company.Product.Audio
{
    // Converts a 0–1 volume slider to the decibels an exposed AudioMixer parameter expects, and back.
    public static class AudioVolume
    {
        public const float SilentDecibels = -80f;

        private const float SilentLinear = 0.0001f;

        public static float ToDecibels(float linear) =>
            linear <= SilentLinear ? SilentDecibels : Mathf.Max(SilentDecibels, Mathf.Log10(linear) * 20f);

        public static float ToLinear(float decibels) =>
            decibels <= SilentDecibels ? 0f : Mathf.Pow(10f, decibels / 20f);
    }
}
