using UnityEngine;

namespace Company.Product.Audio
{
    [CreateAssetMenu(menuName = "Company.Product/Audio/Audio Service Settings", fileName = "AudioServiceSettings")]
    public sealed class AudioServiceSettings : ScriptableObject
    {
        [Tooltip("AudioSources created during loading. Size it to the peak number of sounds playing at once.")]
        [SerializeField, Min(1)] private int _prewarmedVoices = 16;

        [Tooltip("Upper bound on pooled AudioSources.")]
        [SerializeField, Min(1)] private int _maxVoices = 64;

        public int PrewarmedVoices => _prewarmedVoices;

        public int MaxVoices => _maxVoices;
    }
}
