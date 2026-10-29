using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using Company.Product.Core.Algorithms;
using NUnit.Framework;
using UnityEngine;

namespace Company.Product.Core.Tests.Algorithms
{
    public sealed class SpatialHashRadiusTests
    {
        // A radius that covers everything must find everything and return. Runs off the main thread so a hang
        // fails the test instead of the run.
        [TestCase(float.PositiveInfinity)]
        [TestCase(float.MaxValue)]
        [TestCase(3e9f)]
        public void SpatialHash_QueryWithAHugeRadius_ReturnsEveryItem(float radius)
        {
            var hash = new SpatialHash<string>(1f);
            hash.Add("a", Vector3.zero);
            hash.Add("b", new Vector3(50f, 0f, 0f));
            var results = new List<string>();

            var query = Task.Run(() => hash.Query(Vector3.zero, radius, results));

            Assert.That(query.Wait(TimeSpan.FromSeconds(5)), Is.True, $"Query(radius: {radius}) didn't return within 5 seconds.");
            Assert.That(results, Is.EquivalentTo(new[] { "a", "b" }));
        }

        [TestCase(-1f)]
        [TestCase(float.NaN)]
        public void SpatialHash_QueryWithANegativeOrNaNRadius_Throws(float radius)
        {
            var hash = new SpatialHash<string>(1f);

            Assert.Throws<ArgumentOutOfRangeException>(() => hash.Query(Vector3.zero, radius, new List<string>()));
        }
    }
}
