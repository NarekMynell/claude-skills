using System;
using System.Runtime.CompilerServices;
using Company.Product.Core.Extensions;
using Company.Product.Core.Logging;
using Company.Product.Core.Pooling;
using UnityEngine;
using VContainer.Unity;
using Object = UnityEngine.Object;
using Random = System.Random;

namespace Company.Product.Audio
{
    // Plays AudioCues on pooled AudioSources. Register it in the root scope: its voices live under a
    // DontDestroyOnLoad object, and its Tick returns finished voices to the pool.
    public sealed class AudioService : IAudioService, ITickable, IDisposable
    {
        private readonly GameObject _root;
        private readonly ComponentPool<AudioSource> _pool;
        private readonly VoiceTracker _voices = new VoiceTracker();
        // Weak keys: remembering a cue's last clip must not keep the cue and its clips from unloading.
        private readonly ConditionalWeakTable<AudioCue, LastClip> _lastClips = new ConditionalWeakTable<AudioCue, LastClip>();
        private readonly Random _random = new Random();
        private int _nextId;

        public AudioService(AudioServiceSettings settings)
        {
            if (settings == null) throw new ArgumentNullException(nameof(settings));

            _root = new GameObject("[Audio]");
            if (Application.isPlaying) Object.DontDestroyOnLoad(_root);
            _pool = new ComponentPool<AudioSource>(new AudioSourceFactory(_root.transform), _root.transform, settings.PrewarmedVoices, settings.MaxVoices);
            _pool.Prewarm(settings.PrewarmedVoices);
        }

        public AudioHandle Play(AudioCue cue) => Start(cue, Vector3.zero);

        public AudioHandle PlayAt(AudioCue cue, Vector3 position) => Start(cue, position);

        public bool IsPlaying(AudioHandle handle) => handle.IsValid && _voices.IndexOf(handle.Id) >= 0;

        public void Stop(AudioHandle handle)
        {
            if (!handle.IsValid) return;

            var index = _voices.IndexOf(handle.Id);
            if (index >= 0) Release(index);
        }

        public void StopAll()
        {
            for (var i = _voices.Count - 1; i >= 0; i--) Release(i);
        }

        public void Tick()
        {
            // While the listener is paused isPlaying is false, but the voices aren't finished.
            var listenerPaused = AudioListener.pause;
            for (var i = _voices.Count - 1; i >= 0; i--)
            {
                var source = _voices[i].Source;
                if (!source.IsAlive())
                {
                    Release(i);
                    continue;
                }

                if (listenerPaused && !source.ignoreListenerPause) continue;
                if (!source.isPlaying) Release(i);
            }
        }

        public void Dispose()
        {
            StopAll();
            _pool.Dispose();
            _root.SafeDestroy();
        }

        private AudioHandle Start(AudioCue cue, Vector3 position)
        {
            if (cue == null) throw new ArgumentNullException(nameof(cue));
            if (cue.ClipCount == 0)
            {
                Log.Warning($"{cue.name}: no clips to play.", cue);
                return default;
            }

            if (_voices.CountOf(cue) >= cue.MaxInstances) Release(_voices.IndexOfOldest(cue));

            var source = _pool.Spawn(position, Quaternion.identity, _root.transform);
            source.clip = cue.GetClip(PickClip(cue));
            source.outputAudioMixerGroup = cue.Output;
            source.volume = Mathf.Clamp01(cue.Volume * (1f + Vary(cue.VolumeVariation)));
            source.pitch = cue.Pitch * (1f + Vary(cue.PitchVariation));
            source.spatialBlend = cue.SpatialBlend;
            source.loop = cue.Loop;
            source.Play();

            var id = ++_nextId;
            _voices.Add(id, cue, source);
            return new AudioHandle(id);
        }

        private int PickClip(AudioCue cue)
        {
            var count = cue.ClipCount;
            var last = _lastClips.GetValue(cue, _ => new LastClip());
            var index = _random.Next(count);
            if (count > 1 && index == last.Index) index = (index + 1 + _random.Next(count - 1)) % count;

            last.Index = index;
            return index;
        }

        private float Vary(float amount) => amount <= 0f ? 0f : (float)(_random.NextDouble() * 2.0 - 1.0) * amount;

        private void Release(int index)
        {
            var source = _voices[index].Source;
            _voices.RemoveAt(index);
            if (!source.IsAlive()) return;

            source.Stop();
            source.clip = null;
            _pool.Despawn(source);
        }

        private sealed class LastClip
        {
            public int Index { get; set; } = -1;
        }
    }
}
