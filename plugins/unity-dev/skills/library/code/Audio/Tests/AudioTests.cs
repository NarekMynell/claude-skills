using NUnit.Framework;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Company.Product.Audio.Tests
{
    public sealed class AudioTests
    {
        [Test]
        public void VoiceTracker_FindsTheOldestVoiceOfACue_AndCountsPerCue()
        {
            var shot = ScriptableObject.CreateInstance<AudioCue>();
            var step = ScriptableObject.CreateInstance<AudioCue>();
            var tracker = new VoiceTracker();
            tracker.Add(1, shot, null);
            tracker.Add(2, step, null);
            tracker.Add(3, shot, null);

            Assert.That(tracker.CountOf(shot), Is.EqualTo(2));
            Assert.That(tracker[tracker.IndexOfOldest(shot)].Id, Is.EqualTo(1));

            tracker.RemoveAt(tracker.IndexOf(1));
            Assert.That(tracker[tracker.IndexOfOldest(shot)].Id, Is.EqualTo(3));
            Assert.That(tracker.IndexOf(1), Is.EqualTo(-1));

            Object.DestroyImmediate(shot);
            Object.DestroyImmediate(step);
        }

        [TestCase(1f, 0f)]
        [TestCase(0.5f, -6.0206f)]
        [TestCase(0f, AudioVolume.SilentDecibels)]
        public void Volume_ConvertsBetweenLinearAndDecibels(float linear, float decibels)
        {
            Assert.That(AudioVolume.ToDecibels(linear), Is.EqualTo(decibels).Within(1e-3f));
            Assert.That(AudioVolume.ToLinear(decibels), Is.EqualTo(linear).Within(1e-3f));
        }

        [Test]
        public void HandleOfANeverPlayedSound_IsInvalid()
        {
            Assert.That(default(AudioHandle).IsValid, Is.False);
        }
    }
}
