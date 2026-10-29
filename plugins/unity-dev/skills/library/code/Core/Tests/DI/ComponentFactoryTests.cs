using System;
using Company.Product.Core.DI;
using NUnit.Framework;
using UnityEngine;
using VContainer;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.DI
{
    public sealed class ComponentFactoryTests
    {
        private sealed class Marker : MonoBehaviour { }

        // A factory given a parent never puts instances somewhere else: a destroyed parent is a lifetime bug to surface.
        [Test]
        public void Create_AfterItsParentWasDestroyed_Throws()
        {
            var resolver = new ContainerBuilder().Build();
            var prefab = new GameObject("Prefab").AddComponent<Marker>();
            var parent = new GameObject("Parent");
            var factory = new ComponentFactory<Marker>(resolver, prefab, parent.transform);

            var first = factory.Create();
            Assert.That(first.transform.parent, Is.SameAs(parent.transform));

            Object.DestroyImmediate(parent);
            Assert.Throws<InvalidOperationException>(() => factory.Create());

            Object.DestroyImmediate(prefab.gameObject);
            resolver.Dispose();
        }
    }
}
