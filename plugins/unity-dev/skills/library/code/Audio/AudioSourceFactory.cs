using ProjectName.Core.DI;
using UnityEngine;

namespace ProjectName.Audio
{
    internal sealed class AudioSourceFactory : IFactory<AudioSource>
    {
        private readonly Transform _parent;

        public AudioSourceFactory(Transform parent) => _parent = parent;

        // The object every voice lives under. In Play Mode it outlives scene loads.
        public static GameObject CreateRoot()
        {
            var root = new GameObject("[Audio]");
            if (Application.isPlaying) Object.DontDestroyOnLoad(root);
            return root;
        }

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
