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
    // An instance destroyed outside the pool, for example with its scene, is forgotten: despawning it does
    // nothing, and it is never spawned again.
    public sealed class ComponentPool<T> : IDisposable where T : Component
    {
        private readonly IFactory<T> _factory;
        private readonly Transform _container;
        private readonly ObjectPool<T> _pool;
        private readonly Dictionary<T, Instance> _instances = new Dictionary<T, Instance>();
        private readonly int _maxSize;
        private bool _isDisposed;

        // The container is an active GameObject that the pool's owner keeps for the pool's lifetime: inactive
        // instances wait under it, and new ones run Awake there, during loading instead of at their first spawn.
        public ComponentPool(IFactory<T> factory, Transform container, int defaultCapacity = 16, int maxSize = 1024)
        {
            _factory = factory ?? throw new ArgumentNullException(nameof(factory));
            if (container == null) throw new ArgumentNullException(nameof(container));

            _container = container;
            _maxSize = maxSize;
            // No collection check: it scans the whole pool on every release, and Despawn already refuses a second despawn.
            _pool = new ObjectPool<T>(CreateItem, null, OnRelease, DestroyItem, false, defaultCapacity, maxSize);
            SceneManager.sceneUnloaded += OnSceneUnloaded;
        }

        public int CountActive { get; private set; }

        public int CountInactive => _pool.CountInactive;

        // Makes at least `count` instances wait inactive. Call it during loading: creating instances at first use is a frame spike.
        public void Prewarm(int count)
        {
            ThrowIfDisposed();
            if (count < 0 || count > _maxSize) throw new ArgumentOutOfRangeException(nameof(count), $"Prewarm takes 0 to the pool's maxSize ({_maxSize}).");

            var taken = ListPool<T>.Get();
            try
            {
                for (var i = 0; i < count; i++) taken.Add(TakeAlive());
            }
            finally
            {
                // Also when a create fails partway: what was created waits in the pool, so Dispose destroys it.
                for (var i = 0; i < taken.Count; i++) _pool.Release(taken[i]);
                ListPool<T>.Release(taken);
            }
        }

        public T Spawn(Transform parent = null)
        {
            ThrowIfDisposed();
            var item = TakeAlive();
            Place(item, parent);
            Activate(item);
            return item;
        }

        public T Spawn(Vector3 position, Quaternion rotation, Transform parent = null)
        {
            ThrowIfDisposed();
            var item = TakeAlive();
            Place(item, parent);
            item.transform.SetPositionAndRotation(position, rotation);
            Activate(item);
            return item;
        }

        // After Dispose, a despawned instance is destroyed: the pool it would return to is gone.
        public void Despawn(T item)
        {
            if (ReferenceEquals(item, null)) throw new ArgumentNullException(nameof(item));
            if (!_instances.TryGetValue(item, out var instance))
            {
                if (item == null) return; // Destroyed with its scene and already forgotten.

                throw new ArgumentException($"{item.name} doesn't belong to this pool.", nameof(item));
            }

            if (!instance.IsSpawned) throw new InvalidOperationException($"{NameOf(item)} is already in the pool.");

            instance.IsSpawned = false;
            CountActive--;
            if (item == null)
            {
                _instances.Remove(item);
                return;
            }

            var poolables = instance.Poolables;
            try
            {
                for (var i = 0; i < poolables.Length; i++) poolables[i].OnDespawned();
            }
            finally
            {
                if (_isDisposed)
                {
                    _instances.Remove(item);
                    item.gameObject.SafeDestroy();
                }
                else
                {
                    _pool.Release(item);
                }
            }
        }

        // Destroys the inactive instances. Active ones stay with their users.
        public void Dispose()
        {
            if (_isDisposed) return;

            _isDisposed = true;
            SceneManager.sceneUnloaded -= OnSceneUnloaded;
            _pool.Clear();
        }

        private static string NameOf(T item) => item != null ? item.name : "A destroyed object";

        // A reused instance starts from the local pose it was created with, as a fresh one does.
        private void Place(T item, Transform parent)
        {
            var instance = _instances[item];
            item.transform.SetParent(parent, false);
            item.transform.SetLocalPositionAndRotation(instance.LocalPosition, instance.LocalRotation);
            item.transform.localScale = instance.LocalScale;
            if (parent != null) return;

            var activeScene = SceneManager.GetActiveScene();
            if (item.gameObject.scene != activeScene) SceneManager.MoveGameObjectToScene(item.gameObject, activeScene);
        }

        // Skips instances destroyed while they waited in the pool, for example together with a destroyed container.
        private T TakeAlive()
        {
            var item = _pool.Get();
            while (item == null)
            {
                _instances.Remove(item);
                item = _pool.Get();
            }

            return item;
        }

        private void Activate(T item)
        {
            var instance = _instances[item];
            instance.IsSpawned = true;
            CountActive++;
            item.gameObject.SetActive(true);
            var poolables = instance.Poolables;
            // A callback that despawns the instance ends the spawn: the rest get no OnSpawned.
            for (var i = 0; i < poolables.Length && instance.IsSpawned; i++) poolables[i].OnSpawned();
        }

        private T CreateItem()
        {
            if (_container == null) throw new InvalidOperationException($"The container of the {typeof(T).Name} pool was destroyed: dispose a pool before its container.");

            var item = _factory.Create();
            item.gameObject.SetActive(false);
            item.transform.SetParent(_container, false);
            var transform = item.transform;
            _instances.Add(item, new Instance(item.GetComponentsInChildren<IPoolable>(true), transform.localPosition, transform.localRotation, transform.localScale));
            return item;
        }

        private void OnRelease(T item)
        {
            item.gameObject.SetActive(false);
            item.transform.SetParent(_container, false);
        }

        private void DestroyItem(T item)
        {
            _instances.Remove(item);
            if (item != null) item.gameObject.SafeDestroy();
        }

        // Spawned instances that were parented to a scene's objects, or joined it, are destroyed with the scene.
        private void OnSceneUnloaded(Scene scene)
        {
            var destroyed = ListPool<T>.Get();
            try
            {
                foreach (var pair in _instances)
                    if (pair.Key == null && pair.Value.IsSpawned) destroyed.Add(pair.Key);

                CountActive -= destroyed.Count;
                for (var i = 0; i < destroyed.Count; i++) _instances.Remove(destroyed[i]);
            }
            finally
            {
                ListPool<T>.Release(destroyed);
            }
        }

        private void ThrowIfDisposed()
        {
            if (_isDisposed) throw new ObjectDisposedException($"ComponentPool<{typeof(T).Name}>");
        }

        private sealed class Instance
        {
            public Instance(IPoolable[] poolables, Vector3 localPosition, Quaternion localRotation, Vector3 localScale)
            {
                Poolables = poolables;
                LocalPosition = localPosition;
                LocalRotation = localRotation;
                LocalScale = localScale;
            }

            public IPoolable[] Poolables { get; }

            public Vector3 LocalPosition { get; }

            public Quaternion LocalRotation { get; }

            public Vector3 LocalScale { get; }

            public bool IsSpawned { get; set; }
        }
    }
}
