using Company.Product.Core.DI;
using UnityEngine;

namespace Company.Product.Audio
{
    internal sealed class AudioSourceFactory : IFactory<AudioSource>
    {
        private readonly Transform _parent;

        public AudioSourceFactory(Transform parent) => _parent = parent;

        public AudioSource Create()
        {
            var voice = new GameObject("AudioVoice");
            voice.transform.SetParent(_parent, false);
            var source = voice.AddComponent<AudioSource>();
            source.playOnAwake = false;
            return source;
        }
    }
}
