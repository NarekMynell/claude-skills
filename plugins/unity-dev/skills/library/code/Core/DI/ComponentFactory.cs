using System;
using UnityEngine;
using UnityEngine.SceneManagement;
using VContainer;
using VContainer.Unity;

namespace Company.Product.Core.DI
{
    // Instantiates a prefab through the resolver, so the new hierarchy receives its [Inject] dependencies.
    // Without a parent, the instance joins the active scene, like Object.Instantiate. VContainer alone would put it
    // in DontDestroyOnLoad when the resolver belongs to the root scope, so it would outlive every scene.
    // The caller owns what Create returns: the container never destroys it.
    public sealed class ComponentFactory<T> : IFactory<T> where T : Component
    {
        private readonly IObjectResolver _resolver;
        private readonly T _prefab;
        private readonly Transform _parent;

        public ComponentFactory(IObjectResolver resolver, T prefab, Transform parent = null)
        {
            _resolver = resolver ?? throw new ArgumentNullException(nameof(resolver));
            if (prefab == null) throw new ArgumentNullException(nameof(prefab));

            _prefab = prefab;
            _parent = parent;
        }

        public T Create()
        {
            if (_parent != null) return _resolver.Instantiate(_prefab, _parent);

            var instance = _resolver.Instantiate(_prefab);
            var activeScene = SceneManager.GetActiveScene();
            if (instance.gameObject.scene != activeScene) SceneManager.MoveGameObjectToScene(instance.gameObject, activeScene);
            return instance;
        }
    }
}
