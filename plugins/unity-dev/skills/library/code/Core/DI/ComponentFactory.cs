using System;
using UnityEngine;
using VContainer;
using VContainer.Unity;

namespace Company.Product.Core.DI
{
    // Instantiates a prefab through the resolver, so the new hierarchy receives its [Inject] dependencies.
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

        public T Create() => _parent != null ? _resolver.Instantiate(_prefab, _parent) : _resolver.Instantiate(_prefab);
    }
}
