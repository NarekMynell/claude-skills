using System;
using Company.Product.Core.DI;
using Company.Product.Core.Pooling;
using NUnit.Framework;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.Pooling
{
    public sealed class ComponentPoolCallbackTests
    {
        private sealed class FailsOnceOnDespawn : MonoBehaviour, IPoolable
        {
            public bool Fail { get; set; } = true;

            public void OnSpawned() { }

            public void OnDespawned()
            {
                if (!Fail) return;

                Fail = false;
                throw new InvalidOperationException("OnDespawned failed.");
            }
        }

        private sealed class Factory : IFactory<FailsOnceOnDespawn>
        {
            public FailsOnceOnDespawn Create() => new GameObject("Item").AddComponent<FailsOnceOnDespawn>();
        }

        // After a throwing OnDespawned the instance must still end up somewhere the pool can account for:
        // back in the pool, or still spawned so that a retry works. Here it is neither.
        [Test]
        public void ThrowingOnDespawned_DoesNotLoseTheInstance()
        {
            var container = new GameObject("Pool");
            var pool = new ComponentPool<FailsOnceOnDespawn>(new Factory(), container.transform);
            var item = pool.Spawn(container.transform);

            Assert.Throws<InvalidOperationException>(() => pool.Despawn(item));
            var activeAfterFailure = item.gameObject.activeSelf;
            var inactiveCount = pool.CountInactive;
            var activeCount = pool.CountActive;
            Exception retry = null;
            try
            {
                pool.Despawn(item);
            }
            catch (Exception exception)
            {
                retry = exception;
            }

            pool.Dispose();
            var survivedDispose = item != null;
            Object.DestroyImmediate(container);

            var backInPool = !activeAfterFailure && inactiveCount == 1;
            var stillSpawned = activeAfterFailure && activeCount == 1 && retry == null;
            var failures = new System.Collections.Generic.List<string>();
            if (!backInPool && !stillSpawned)
                failures.Add($"Lost: active {activeAfterFailure}, CountActive {activeCount}, CountInactive {inactiveCount}, retry: {retry?.Message ?? "ok"}");
            if (survivedDispose && !stillSpawned) failures.Add("It survived Dispose.");
            Assert.That(failures, Is.Empty);
        }
    }
}
