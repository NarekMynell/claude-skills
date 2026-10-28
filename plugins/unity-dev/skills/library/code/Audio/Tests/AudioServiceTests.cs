using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;
using Object = UnityEngine.Object;

namespace Company.Product.Audio.Tests
{
    public sealed class AudioServiceTests
    {
        private AudioServiceSettings _settings;
        private AudioCue _cue;
        private AudioClip _clip;
        private AudioService _service;

        [SetUp]
        public void SetUp()
        {
            _settings = ScriptableObject.CreateInstance<AudioServiceSettings>();
            _clip = AudioClip.Create("Tone", 4410, 1, 44100, false);
            _cue = ScriptableObject.CreateInstance<AudioCue>();
            var cue = new SerializedObject(_cue);
            var clips = cue.FindProperty("_clips");
            clips.arraySize = 1;
            clips.GetArrayElementAtIndex(0).objectReferenceValue = _clip;
            cue.FindProperty("_maxInstances").intValue = 2;
            cue.ApplyModifiedPropertiesWithoutUndo();
            _service = new AudioService(_settings);
        }

        [TearDown]
        public void TearDown()
        {
            _service.Dispose();
            Object.DestroyImmediate(_cue);
            Object.DestroyImmediate(_clip);
            Object.DestroyImmediate(_settings);
        }

        [Test]
        public void PlayingBeyondMaxInstances_StopsTheOldestInstance()
        {
            var first = _service.Play(_cue);
            var second = _service.Play(_cue);
            var third = _service.PlayAt(_cue, Vector3.one);

            Assert.That(_service.IsPlaying(first), Is.False);
            Assert.That(_service.IsPlaying(second), Is.True);
            Assert.That(_service.IsPlaying(third), Is.True);
        }

        [Test]
        public void Tick_ReturnsFinishedVoices_ButKeepsThemWhileTheListenerIsPaused()
        {
            var handle = _service.Play(_cue);
            foreach (var source in Object.FindObjectsByType<AudioSource>()) source.Stop();

            AudioListener.pause = true;
            try
            {
                _service.Tick();
                Assert.That(_service.IsPlaying(handle), Is.True);
            }
            finally
            {
                AudioListener.pause = false;
            }

            _service.Tick();
            Assert.That(_service.IsPlaying(handle), Is.False);
        }

        [Test]
        public void Play_AfterWarmup_DoesNotAllocate()
        {
            _service.Play(_cue);
            _service.Play(_cue);
            _service.Play(_cue);

            Assert.That(() => { _service.Play(_cue); }, Is.Not.AllocatingGCMemory());
        }

        [Test]
        public void Stop_AndStopAll_EndTheSounds()
        {
            var first = _service.Play(_cue);
            var second = _service.Play(_cue);

            _service.Stop(first);
            Assert.That(_service.IsPlaying(first), Is.False);
            Assert.That(_service.IsPlaying(second), Is.True);

            _service.StopAll();
            Assert.That(_service.IsPlaying(second), Is.False);
            Assert.That(_service.IsPlaying(default), Is.False);
        }
    }
}
