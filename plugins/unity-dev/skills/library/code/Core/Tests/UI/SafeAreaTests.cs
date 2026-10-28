using Company.Product.Core.UI;
using NUnit.Framework;
using UnityEngine;
using Is = UnityEngine.TestTools.Constraints.Is;

namespace Company.Product.Core.Tests.UI
{
    public sealed class SafeAreaTests
    {
        [Test]
        public void Anchors_MatchTheSafeAreaAsAFractionOfTheScreen()
        {
            var (min, max) = SafeArea.CalculateAnchors(new Rect(0f, 102f, 1170f, 2289f), new Vector2Int(1170, 2532));

            Assert.That(min.x, Is.EqualTo(0f));
            Assert.That(min.y, Is.EqualTo(102f / 2532f).Within(1e-6f));
            Assert.That(max.x, Is.EqualTo(1f));
            Assert.That(max.y, Is.EqualTo(2391f / 2532f).Within(1e-6f));
        }

        [Test]
        public void Anchors_AreClampedToTheScreen()
        {
            var (min, max) = SafeArea.CalculateAnchors(new Rect(-10f, -10f, 1100f, 2100f), new Vector2Int(1000, 2000));

            Assert.That(min, Is.EqualTo(Vector2.zero));
            Assert.That(max, Is.EqualTo(Vector2.one));
        }
    }
}
