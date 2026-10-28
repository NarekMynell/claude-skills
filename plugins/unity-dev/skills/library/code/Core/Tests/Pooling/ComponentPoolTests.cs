using System;
using Company.Product.Core.DI;
using Company.Product.Core.Pooling;
using NUnit.Framework;
using UnityEngine;
using Is = UnityEngine.TestTools.Constraints.Is;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.Pooling
{
    public sealed class ComponentPoolTests
    {
        private GameObject _container;

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

        [TearDown]
        public void TearDown() => Object.DestroyImmediate(_container);

        [Test]
        public void Prewarm_CreatesInactiveInstances_WithoutSpawnCallbacks()
        {
            var factory = new BulletFactory();
            var pool = new ComponentPool<Bullet>(factory, _container.transform);

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
            var pool = new ComponentPool<Bullet>(factory, _container.transform);

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
            var pool = new ComponentPool<Bullet>(new BulletFactory(), _container.transform);
            var stranger = new GameObject("Stranger").AddComponent<Bullet>();

            Assert.Throws<ArgumentException>(() => pool.Despawn(stranger));
            Object.DestroyImmediate(stranger.gameObject);
        }

        [Test]
        public void DespawningTwice_Throws_WithoutCallingOnDespawnedAgain()
        {
            var pool = new ComponentPool<Bullet>(new BulletFactory(), _container.transform);
            var bullet = pool.Spawn(_container.transform);
            pool.Despawn(bullet);

            Assert.Throws<InvalidOperationException>(() => pool.Despawn(bullet));
            Assert.That(bullet.Despawned, Is.EqualTo(1));
        }

        [Test]
        public void Dispose_DestroysTheInactiveInstances()
        {
            var pool = new ComponentPool<Bullet>(new BulletFactory(), _container.transform);
            pool.Prewarm(3);

            pool.Dispose();

            Assert.That(_container.transform.childCount, Is.Zero);
        }
    }
}
