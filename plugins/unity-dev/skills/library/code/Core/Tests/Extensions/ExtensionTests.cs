using System;
using System.Collections.Generic;
using Company.Product.Core.Extensions;
using NUnit.Framework;
using UnityEngine;
using Is = UnityEngine.TestTools.Constraints.Is;
using Object = UnityEngine.Object;

namespace Company.Product.Core.Tests.Extensions
{
    public sealed class ExtensionTests
    {
        private interface IDamageable
        {
        }

        private sealed class DamageableBehaviour : MonoBehaviour, IDamageable
        {
        }

        [Test]
        public void IsAlive_SeesThroughAnInterface_ThatTheObjectWasDestroyed()
        {
            var gameObject = new GameObject("Target");
            IDamageable target = gameObject.AddComponent<DamageableBehaviour>();
            Object.DestroyImmediate(gameObject);

            Assert.That(target != null, Is.True, "A plain null check passes on a destroyed object behind an interface.");
            Assert.That(target.IsAlive(), Is.False);
            Assert.That(target.OrNull(), Is.Null);
        }

        [Test]
        public void IsAlive_ForPlainObjects_IsANullCheck()
        {
            object value = "text";

            Assert.That(value.IsAlive(), Is.True);
            Assert.That(((object)null).IsAlive(), Is.False);
        }

        [Test]
        public void SwapRemoveAt_MovesTheLastElementIntoTheGap()
        {
            var list = new List<int> { 1, 2, 3, 4 };
            list.SwapRemoveAt(1);

            Assert.That(list, Is.EqualTo(new[] { 1, 4, 3 }));
            Assert.Throws<ArgumentOutOfRangeException>(() => list.SwapRemoveAt(3));
        }

        [Test]
        public void VectorAndColorHelpers_ReplaceOneComponent()
        {
            Assert.That(new Vector3(1f, 2f, 3f).WithY(9f), Is.EqualTo(new Vector3(1f, 9f, 3f)));
            Assert.That(new Vector3(1f, 2f, 3f).ToXZ(), Is.EqualTo(new Vector2(1f, 3f)));
            Assert.That(new Vector2(1f, 3f).FromXZ(5f), Is.EqualTo(new Vector3(1f, 5f, 3f)));
            Assert.That(Color.red.WithAlpha(0.5f), Is.EqualTo(new Color(1f, 0f, 0f, 0.5f)));
        }

        [Test]
        public void DestroyChildren_AndSetLayerRecursively_CoverTheHierarchy()
        {
            var root = new GameObject("Root");
            var child = new GameObject("Child");
            child.transform.SetParent(root.transform);
            new GameObject("Grandchild").transform.SetParent(child.transform);

            root.SetLayerRecursively(5);
            Assert.That(child.transform.GetChild(0).gameObject.layer, Is.EqualTo(5));

            root.transform.DestroyChildren();
            Assert.That(root.transform.childCount, Is.Zero);
            Object.DestroyImmediate(root);
        }
    }
}
