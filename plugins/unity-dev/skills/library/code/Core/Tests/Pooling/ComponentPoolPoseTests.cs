using Company.Product.Core.DI;
using Company.Product.Core.Pooling;
using NUnit.Framework;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.Pooling
{
    public sealed class ComponentPoolPoseTests
    {
        private sealed class Item : MonoBehaviour
        {
        }

        private sealed class Factory : IFactory<Item>
        {
            public Item Create() => new GameObject("Item").AddComponent<Item>();
        }

        // Spawn(parent) of a reused instance must give the pose the first Spawn(parent) gave, as
        // Object.Instantiate(prefab, parent) would; here it gives wherever the previous use left it.
        [Test]
        public void SpawnUnderAParent_OfAReusedInstance_StartsAtTheSamePoseAsAFreshOne()
        {
            var container = new GameObject("Pool");
            var parent = new GameObject("Parent").transform;
            var pool = new ComponentPool<Item>(new Factory(), container.transform);

            var first = pool.Spawn(parent);
            var freshPosition = first.transform.localPosition;
            var freshScale = first.transform.localScale;
            first.transform.localPosition = new Vector3(5f, 5f, 5f);   // gameplay moves and scales it
            first.transform.localScale = Vector3.one * 3f;
            pool.Despawn(first);

            var reused = pool.Spawn(parent);
            var reusedPosition = reused.transform.localPosition;
            var reusedScale = reused.transform.localScale;

            pool.Dispose();
            Object.DestroyImmediate(reused.gameObject);
            Object.DestroyImmediate(parent.gameObject);
            Object.DestroyImmediate(container);

            Assert.That(reused, Is.SameAs(first));
            Assert.That(reusedPosition, Is.EqualTo(freshPosition), $"Reused at {reusedPosition}, scale {reusedScale}.");
            Assert.That(reusedScale, Is.EqualTo(freshScale));
        }

        // README: "Prewarm(n) makes at least n instances wait inactive".
        [Test]
        public void Prewarm_BeyondMaxSize_KeepsTheRequestedCount_OrRefuses()
        {
            var container = new GameObject("Pool");
            var factory = new CountingFactory();
            var pool = new ComponentPool<Item>(factory, container.transform, defaultCapacity: 4, maxSize: 4);

            System.Exception refused = null;
            try
            {
                pool.Prewarm(10);
            }
            catch (System.Exception exception)
            {
                refused = exception;
            }

            var inactive = pool.CountInactive;
            pool.Dispose();
            Object.DestroyImmediate(container);

            Assert.That(refused != null || inactive >= 10, Is.True,
                $"Prewarm(10) created {factory.Created} instances, destroyed {factory.Created - inactive} of them, and keeps {inactive}.");
        }

        private sealed class CountingFactory : IFactory<Item>
        {
            public int Created { get; private set; }

            public Item Create()
            {
                Created++;
                return new GameObject("Item").AddComponent<Item>();
            }
        }
    }
}
