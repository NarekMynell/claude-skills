using System;
using System.Collections.Generic;
using Company.Product.Core.DI;
using Company.Product.Core.Pooling;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.Pooling
{
    public sealed class ComponentPoolTests
    {
        private GameObject _container;
        private readonly List<ComponentPool<Bullet>> _pools = new List<ComponentPool<Bullet>>();

        private sealed class Bullet : MonoBehaviour, IPoolable
        {
            public int Spawned { get; private set; }

            public int Despawned { get; private set; }

            public void OnSpawned() => Spawned++;

            public void OnDespawned() => Despawned++;
        }

        private sealed class BulletFactory : IFactory<Bullet>
        {
            public int Created { get; private set; }

            public Bullet Create()
            {
                Created++;
                return new GameObject("Bullet").AddComponent<Bullet>();
            }
        }

        [SetUp]
        public void SetUp() => _container = new GameObject("Pool");

        // Pools subscribe to a static scene event, so every pool a test creates is disposed.
        [TearDown]
        public void TearDown()
        {
            foreach (var pool in _pools) pool.Dispose();
            _pools.Clear();
            Object.DestroyImmediate(_container);
        }

        private ComponentPool<Bullet> CreatePool(BulletFactory factory = null)
        {
            var pool = new ComponentPool<Bullet>(factory ?? new BulletFactory(), _container.transform);
            _pools.Add(pool);
            return pool;
        }

        [Test]
        public void Prewarm_CreatesInactiveInstances_WithoutSpawnCallbacks()
        {
            var factory = new BulletFactory();
            var pool = CreatePool(factory);

            pool.Prewarm(5);
            pool.Prewarm(3);

            Assert.That(factory.Created, Is.EqualTo(5));
            Assert.That(pool.CountInactive, Is.EqualTo(5));
            Assert.That(_container.transform.childCount, Is.EqualTo(5));
            Assert.That(_container.GetComponentsInChildren<Bullet>(true), Has.All.Matches<Bullet>(bullet => bullet.Spawned == 0 && !bullet.gameObject.activeSelf));
        }

        [Test]
        public void SpawnAndDespawn_ReuseTheSameInstance_AndCallTheCallbacks()
        {
            var factory = new BulletFactory();
            var pool = CreatePool(factory);

            var bullet = pool.Spawn(new Vector3(1f, 2f, 3f), Quaternion.identity);
            Assert.That(bullet.gameObject.activeSelf, Is.True);
            Assert.That(bullet.transform.position, Is.EqualTo(new Vector3(1f, 2f, 3f)));
            Assert.That(bullet.Spawned, Is.EqualTo(1));

            pool.Despawn(bullet);
            Assert.That(bullet.gameObject.activeSelf, Is.False);
            Assert.That(bullet.Despawned, Is.EqualTo(1));

            Assert.That(pool.Spawn(), Is.SameAs(bullet));
            Assert.That(factory.Created, Is.EqualTo(1));
            Object.DestroyImmediate(bullet.gameObject);
        }

        [Test]
        public void Despawn_OfAForeignObject_Throws()
        {
            var pool = CreatePool();
            var stranger = new GameObject("Stranger").AddComponent<Bullet>();

            Assert.Throws<ArgumentException>(() => pool.Despawn(stranger));
            Object.DestroyImmediate(stranger.gameObject);
        }

        [Test]
        public void DespawningTwice_Throws_WithoutCallingOnDespawnedAgain()
        {
            var pool = CreatePool();
            var bullet = pool.Spawn(_container.transform);
            pool.Despawn(bullet);

            Assert.Throws<InvalidOperationException>(() => pool.Despawn(bullet));
            Assert.That(bullet.Despawned, Is.EqualTo(1));
        }

        [Test]
        public void Dispose_DestroysTheInactiveInstances()
        {
            var pool = CreatePool();
            pool.Prewarm(3);

            pool.Dispose();

            Assert.That(_container.transform.childCount, Is.Zero);
        }

        [Test]
        public void Container_IsRequired()
        {
            Assert.Throws<ArgumentNullException>(() => new ComponentPool<Bullet>(new BulletFactory(), null));
        }

        [Test]
        public void Despawn_OfAnInstanceDestroyedOutsideThePool_DoesNothing()
        {
            var pool = CreatePool();
            var bullet = pool.Spawn();
            Object.DestroyImmediate(bullet.gameObject);

            Assert.DoesNotThrow(() => pool.Despawn(bullet));
            Assert.That(pool.CountActive, Is.Zero);
        }

        [Test]
        public void Spawn_SkipsInstancesDestroyedWhileWaiting()
        {
            var factory = new BulletFactory();
            var pool = CreatePool(factory);
            pool.Prewarm(1);
            Object.DestroyImmediate(_container.GetComponentInChildren<Bullet>(true).gameObject);

            var bullet = pool.Spawn(_container.transform);

            Assert.That(bullet != null, Is.True);
            Assert.That(factory.Created, Is.EqualTo(2));
        }

        [Test]
        public void AfterDispose_SpawnThrows_AndADespawnedInstanceIsDestroyed()
        {
            var pool = CreatePool();
            var bullet = pool.Spawn(_container.transform);

            pool.Dispose();
            pool.Dispose();

            Assert.Throws<ObjectDisposedException>(() => pool.Spawn());
            pool.Despawn(bullet);
            Assert.That(bullet == null, Is.True);
            Assert.That(bullet.Despawned, Is.EqualTo(1));
        }

        [Test]
        public void SpawnAndDespawn_DoNotAllocate_OnceWarm()
        {
            var pool = CreatePool();
            pool.Prewarm(1);
            var parent = _container.transform;

            Assert.That(() =>
            {
                var bullet = pool.Spawn(parent);
                pool.Despawn(bullet);
            }, Is.Not.AllocatingGCMemory());
        }
    }
}
