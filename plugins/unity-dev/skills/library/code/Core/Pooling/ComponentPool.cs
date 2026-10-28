using System;
using System.Collections.Generic;
using Company.Product.Core.DI;
using Company.Product.Core.Extensions;
using UnityEngine;
using UnityEngine.Pool;
using UnityEngine.SceneManagement;

namespace Company.Product.Core.Pooling
{
    // Pool of inactive instances built on UnityEngine.Pool. Spawn positions an instance before activating it,
    // then calls IPoolable.OnSpawned on every IPoolable in its hierarchy; Despawn does the reverse.
    // Without a parent, a spawned instance joins the active scene, like Object.Instantiate.
    public sealed class ComponentPool<T> : IDisposable where T : Component
    {
        private readonly IFactory<T> _factory;
        private readonly Transform _container;
        private readonly ObjectPool<T> _pool;
        private readonly Dictionary<T, Instance> _instances = new Dictionary<T, Instance>();

        public ComponentPool(IFactory<T> factory, Transform container, int defaultCapacity = 16, int maxSize = 1024)
        {
            _factory = factory ?? throw new ArgumentNullException(nameof(factory));
            _container = container;
            _pool = new ObjectPool<T>(CreateItem, null, OnRelease, DestroyItem, true, defaultCapacity, maxSize);
        }

        public int CountActive => _pool.CountActive;

        public int CountInactive => _pool.CountInactive;

        // Makes at least `count` instances wait inactive. Call it during loading: creating instances at first use is a frame spike.
        public void Prewarm(int count)
        {
            if (count < 0) throw new ArgumentOutOfRangeException(nameof(count));

            var taken = ListPool<T>.Get();
            try
            {
                for (var i = 0; i < count; i++) taken.Add(_pool.Get());
                for (var i = 0; i < taken.Count; i++) _pool.Release(taken[i]);
            }
            finally
            {
                ListPool<T>.Release(taken);
            }
        }

        public T Spawn(Transform parent = null)
        {
            var item = _pool.Get();
            Place(item, parent);
            Activate(item);
            return item;
        }

        public T Spawn(Vector3 position, Quaternion rotation, Transform parent = null)
        {
            var item = _pool.Get();
            Place(item, parent);
            item.transform.SetPositionAndRotation(position, rotation);
            Activate(item);
            return item;
        }

        public void Despawn(T item)
        {
            if (item == null) throw new ArgumentNullException(nameof(item));
            if (!_instances.TryGetValue(item, out var instance)) throw new ArgumentException($"{item.name} doesn't belong to this pool.", nameof(item));
            if (!instance.IsSpawned) throw new InvalidOperationException($"{item.name} is already in the pool.");

            instance.IsSpawned = false;
            var poolables = instance.Poolables;
            for (var i = 0; i < poolables.Length; i++) poolables[i].OnDespawned();
            _pool.Release(item);
        }

        // Destroys the inactive instances. Active ones stay with their users.
        public void Dispose() => _pool.Clear();

        private static void Place(T item, Transform parent)
        {
            item.transform.SetParent(parent, false);
            if (parent != null) return;

            var activeScene = SceneManager.GetActiveScene();
            if (item.gameObject.scene != activeScene) SceneManager.MoveGameObjectToScene(item.gameObject, activeScene);
        }

        private void Activate(T item)
        {
            var instance = _instances[item];
            instance.IsSpawned = true;
            item.gameObject.SetActive(true);
            var poolables = instance.Poolables;
            for (var i = 0; i < poolables.Length; i++) poolables[i].OnSpawned();
        }

        private T CreateItem()
        {
            var item = _factory.Create();
            item.gameObject.SetActive(false);
            if (_container != null) item.transform.SetParent(_container, false);
            _instances.Add(item, new Instance(item.GetComponentsInChildren<IPoolable>(true)));
            return item;
        }

        private void OnRelease(T item)
        {
            item.gameObject.SetActive(false);
            if (_container != null) item.transform.SetParent(_container, false);
        }

        private void DestroyItem(T item)
        {
            _instances.Remove(item);
            if (item != null) item.gameObject.SafeDestroy();
        }

        private sealed class Instance
        {
            public Instance(IPoolable[] poolables) => Poolables = poolables;

            public IPoolable[] Poolables { get; }

            public bool IsSpawned { get; set; }
        }
    }
}
