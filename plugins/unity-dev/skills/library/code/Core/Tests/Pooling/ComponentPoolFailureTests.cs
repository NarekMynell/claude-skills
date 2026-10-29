using System;
using System.Collections.Generic;
using System.Reflection;
using Company.Product.Core.DI;
using Company.Product.Core.Pooling;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using VContainer;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.Pooling
{
    public sealed class ComponentPoolFailureTests
    {
        private sealed class Plain : MonoBehaviour
        {
        }

        private sealed class MissingService
        {
        }

        private sealed class NeedsMissingService : MonoBehaviour
        {
            [Inject]
            public void Construct(MissingService service)
            {
            }
        }

        private sealed class FailingFactory : IFactory<Plain>
        {
            private readonly int _failAt;

            public FailingFactory(int failAt) => _failAt = failAt;

            public int Created { get; private set; }

            public Plain Create()
            {
                if (++Created == _failAt) throw new InvalidOperationException("Create failed.");

                return new GameObject("Plain").AddComponent<Plain>();
            }
        }

        private sealed class SelfDespawning : MonoBehaviour, IPoolable
        {
            public ComponentPool<SelfDespawning> Pool { get; set; }

            public void OnSpawned() => Pool.Despawn(this);

            public void OnDespawned()
            {
            }
        }

        private sealed class Recorder : MonoBehaviour, IPoolable
        {
            public readonly List<string> Log = new List<string>();

            public void OnSpawned() => Log.Add("spawned");

            public void OnDespawned() => Log.Add("despawned");
        }

        private sealed class SelfDespawningFactory : IFactory<SelfDespawning>
        {
            public SelfDespawning Create()
            {
                var gameObject = new GameObject("SelfDespawning");
                var item = gameObject.AddComponent<SelfDespawning>();
                gameObject.AddComponent<Recorder>();
                return item;
            }
        }

        private GameObject _container;
        private readonly List<GameObject> _created = new List<GameObject>();

        [SetUp]
        public void SetUp() => _container = new GameObject("Pool");

        [TearDown]
        public void TearDown()
        {
            foreach (var created in _created)
                if (created != null) Object.DestroyImmediate(created);

            _created.Clear();
            Object.DestroyImmediate(_container);
        }

        // README: "Dispose destroys the inactive instances".
        [Test]
        public void FailedPrewarm_ThenDispose_LeavesNoInactiveInstanceBehind()
        {
            var pool = new ComponentPool<Plain>(new FailingFactory(failAt: 3), _container.transform);

            Assert.Throws<InvalidOperationException>(() => pool.Prewarm(5));
            pool.Dispose();

            Assert.That(_container.transform.childCount, Is.Zero, "Instances created before the failure outlive Dispose.");
        }

        // A Register that throws hands no pool to the registry, so nothing disposes the pool it created.
        [Test]
        public void Register_WithANegativePrewarmCount_LeavesNoPoolSubscribedToSceneUnloaded()
        {
            var before = PoolsSubscribedToSceneUnloaded();
            var registry = new PrefabPoolRegistry(new ContainerBuilder().Build(), _container.transform);
            var prefab = new GameObject("Prefab").AddComponent<Plain>();
            _created.Add(prefab.gameObject);

            Assert.Throws<ArgumentOutOfRangeException>(() => registry.Register(prefab, prewarmCount: -1));
            registry.Dispose();

            Assert.That(PoolsSubscribedToSceneUnloaded(), Is.EqualTo(before), "The failed Register leaked a pool on a static event.");
        }

        [Test]
        public void Register_WhosePrefabMissesADependency_LeavesNoPoolSubscribedToSceneUnloaded()
        {
            var before = PoolsSubscribedToSceneUnloaded();
            var registry = new PrefabPoolRegistry(new ContainerBuilder().Build(), _container.transform);
            var prefab = new GameObject("Prefab").AddComponent<NeedsMissingService>();
            _created.Add(prefab.gameObject);

            Assert.That(() => registry.Register(prefab, prewarmCount: 4), Throws.Exception);
            registry.Dispose();

            Assert.That(PoolsSubscribedToSceneUnloaded(), Is.EqualTo(before), "The failed Register leaked a pool on a static event.");
        }

        // Spawn must not hand out an instance that is already back in the pool, and no component may get
        // OnSpawned after the instance was despawned.
        [Test]
        public void DespawnFromOnSpawned_DoesNotLeaveTheInstanceSpawnedOrReturned()
        {
            var pool = new ComponentPool<SelfDespawning>(new SelfDespawningFactory(), _container.transform);
            pool.Prewarm(1);
            var prewarmed = _container.GetComponentInChildren<SelfDespawning>(true);
            prewarmed.Pool = pool;
            var recorder = prewarmed.GetComponent<Recorder>();

            var spawned = pool.Spawn(_container.transform);

            try
            {
                Assert.That(recorder.Log, Is.EqualTo(new[] { "despawned" }).Or.EqualTo(new[] { "spawned", "despawned" }),
                    "A component received OnSpawned after its instance was despawned.");
            }
            finally
            {
                pool.Dispose();
                if (spawned != null) Object.DestroyImmediate(spawned.gameObject);
            }
        }

        private static int PoolsSubscribedToSceneUnloaded()
        {
            var field = typeof(SceneManager).GetField("sceneUnloaded", BindingFlags.Static | BindingFlags.NonPublic);
            var handlers = (Delegate)field.GetValue(null);
            if (handlers == null) return 0;

            var count = 0;
            foreach (var handler in handlers.GetInvocationList())
                if (handler.Target != null && handler.Target.GetType().IsGenericType &&
                    handler.Target.GetType().GetGenericTypeDefinition() == typeof(ComponentPool<>))
                    count++;

            return count;
        }
    }
}
