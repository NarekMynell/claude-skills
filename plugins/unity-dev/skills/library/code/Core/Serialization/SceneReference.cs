using System;
using System.IO;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Serialization
{
    // A scene picked in the Inspector as an asset and stored as a path, so a renamed or moved scene
    // updates the path the next time the owner is saved.
    [Serializable]
    public sealed class SceneReference : ISerializationCallbackReceiver
    {
        // Typed as Object, not SceneAsset: SceneAsset is Editor-only, and the reference is simply empty in builds.
        [SerializeField] private Object _sceneAsset;
        [SerializeField] private string _scenePath = string.Empty;

        public string ScenePath => _scenePath;

        public string SceneName => Path.GetFileNameWithoutExtension(_scenePath);

        public bool IsAssigned => !string.IsNullOrEmpty(_scenePath);

        void ISerializationCallbackReceiver.OnBeforeSerialize()
        {
#if UNITY_EDITOR
            if (_sceneAsset == null) return;

            var path = UnityEditor.AssetDatabase.GetAssetPath(_sceneAsset);
            if (!string.IsNullOrEmpty(path)) _scenePath = path;
#endif
        }

        void ISerializationCallbackReceiver.OnAfterDeserialize() { }
    }
}
