using System;
using System.Collections.Generic;
using Company.Product.Core.DI;
using UnityEngine;
using VContainer;

namespace Company.Product.Core.Pooling
{
    // One shared pool per prefab. Pools are registered and prewarmed during loading; asking for an
    // unregistered prefab throws, so a missing prewarm shows up immediately instead of as a spike.
    public sealed class PrefabPoolRegistry : IDisposable
    {
        private readonly IObjectResolver _resolver;
        private readonly Transform _container;
        private readonly Dictionary<Component, IDisposable> _pools = new Dictionary<Component, IDisposable>();
        private bool _isDisposed;

        // The container is an active GameObject that lives as long as the registry: put it in the same scope's prefab or scene.
        public PrefabPoolRegistry(IObjectResolver resolver, Transform container)
        {
            _resolver = resolver ?? throw new ArgumentNullException(nameof(resolver));
            if (container == null) throw new ArgumentNullException(nameof(container));

            _container = container;
        }

        public ComponentPool<T> Register<T>(T prefab, int prewarmCount, int maxSize = 1024) where T : Component
        {
            ThrowIfDisposed();
            if (prefab == null) throw new ArgumentNullException(nameof(prefab));
            if (_pools.ContainsKey(prefab)) throw new InvalidOperationException($"{prefab.name} already has a pool.");
            if (prewarmCount < 0) throw new ArgumentOutOfRangeException(nameof(prewarmCount));

            var factory = new ComponentFactory<T>(_resolver, prefab, _container);
            var pool = new ComponentPool<T>(factory, _container, Mathf.Max(prewarmCount, 1), maxSize);
            try
            {
                pool.Prewarm(prewarmCount);
            }
            catch
            {
                pool.Dispose();
                throw;
            }

            _pools.Add(prefab, pool);
            return pool;
        }

        public ComponentPool<T> Get<T>(T prefab) where T : Component
        {
            ThrowIfDisposed();
            if (prefab == null) throw new ArgumentNullException(nameof(prefab));

            return _pools.TryGetValue(prefab, out var pool)
                ? (ComponentPool<T>)pool
                : throw new InvalidOperationException($"{prefab.name} has no pool. Register it during loading.");
        }

        public void Dispose()
        {
            if (_isDisposed) return;

            _isDisposed = true;
            foreach (var pool in _pools.Values) pool.Dispose();
            _pools.Clear();
        }

        private void ThrowIfDisposed()
        {
            if (_isDisposed) throw new ObjectDisposedException(nameof(PrefabPoolRegistry));
        }
    }
}
