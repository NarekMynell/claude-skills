using System;
using UnityEngine;
using UnityEngine.Audio;

namespace Company.Product.Audio
{
    // One game sound: its variants, mix output and variation. Data only; AudioService plays it.
    [CreateAssetMenu(menuName = "Company.Product/Audio/Audio Cue", fileName = "AudioCue")]
    public sealed class AudioCue : ScriptableObject
    {
        [Tooltip("Variants picked at random, never the same one twice in a row.")]
        [SerializeField] private AudioClip[] _clips = Array.Empty<AudioClip>();
        [SerializeField] private AudioMixerGroup _output;
        [SerializeField, Range(0f, 1f)] private float _volume = 1f;
        [SerializeField, Range(0f, 0.5f)] private float _volumeVariation = 0.05f;
        [SerializeField, Range(0.1f, 3f)] private float _pitch = 1f;
        [SerializeField, Range(0f, 0.5f)] private float _pitchVariation = 0.05f;
        [Tooltip("0 is 2D, 1 is fully 3D.")]
        [SerializeField, Range(0f, 1f)] private float _spatialBlend;
        [Tooltip("Playing it again beyond this count stops its oldest instance.")]
        [SerializeField, Min(1)] private int _maxInstances = 4;
        [SerializeField] private bool _loop;

        public int ClipCount => _clips.Length;
        public AudioMixerGroup Output => _output;
        public float Volume => _volume;
        public float VolumeVariation => _volumeVariation;
        public float Pitch => _pitch;
        public float PitchVariation => _pitchVariation;
        public float SpatialBlend => _spatialBlend;
        public int MaxInstances => _maxInstances;
        public bool Loop => _loop;

        public AudioClip GetClip(int index) => _clips[index];

        private void OnValidate()
        {
            if (_clips.Length == 0) Debug.LogWarning($"{name}: no clips assigned.", this);
            for (var i = 0; i < _clips.Length; i++)
                if (_clips[i] == null) Debug.LogWarning($"{name}: clip {i} is empty.", this);
        }
    }
}
