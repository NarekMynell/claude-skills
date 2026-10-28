using Company.Product.Core.Serialization;
using UnityEngine;

namespace Company.Product.Core.Bootstrap
{
    [CreateAssetMenu(menuName = "Company.Product/Core/First Scene Config", fileName = "FirstSceneConfig")]
    public sealed class FirstSceneConfig : ScriptableObject
    {
        [Tooltip("The scene the startup opens in builds. In the Editor, the scene that was open when Play was pressed opens instead.")]
        [SerializeField] private SceneReference _firstScene = new SceneReference();

        public SceneReference FirstScene => _firstScene;

        private void OnValidate()
        {
            if (!_firstScene.IsAssigned) Debug.LogWarning($"{name}: the first scene isn't assigned.", this);
        }
    }
}
