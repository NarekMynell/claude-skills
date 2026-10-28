using System;
using System.Collections.Generic;
using System.Linq;
using Company.Product.Core.Algorithms;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;
using Random = System.Random;

namespace Company.Product.Core.Tests.Algorithms
{
    public sealed class AlgorithmTests
    {
        [Test]
        public void Shuffle_KeepsEveryElement_AndIsDeterministicPerSeed()
        {
            var first = Enumerable.Range(0, 50).ToList();
            var second = Enumerable.Range(0, 50).ToList();
            first.Shuffle(new Random(3));
            second.Shuffle(new Random(3));

            Assert.That(first, Is.EquivalentTo(Enumerable.Range(0, 50)));
            Assert.That(first, Is.EqualTo(second));
            Assert.That(first, Is.Not.EqualTo(Enumerable.Range(0, 50)));
        }

        [Test]
        public void WeightedPicker_NeverPicksZeroWeight_AndFollowsTheWeights()
        {
            var picker = new WeightedPicker<string>(new[] { "rare", "never", "common" }, new[] { 1f, 0f, 3f });
            var random = new Random(11);
            var counts = new Dictionary<string, int> { ["rare"] = 0, ["never"] = 0, ["common"] = 0 };
            for (var i = 0; i < 40000; i++) counts[picker.Pick(random)]++;

            Assert.That(counts["never"], Is.Zero);
            Assert.That(counts["common"] / (double)counts["rare"], Is.EqualTo(3.0).Within(0.15));
        }

        [Test]
        public void WeightedPicker_RejectsInvalidWeights()
        {
            Assert.Throws<ArgumentException>(() => new WeightedPicker<int>(new[] { 1 }, new[] { 0f }));
            Assert.Throws<ArgumentException>(() => new WeightedPicker<int>(new[] { 1 }, new[] { -1f }));
            Assert.Throws<ArgumentException>(() => new WeightedPicker<int>(new[] { 1, 2 }, new[] { 1f }));
        }

        [Test]
        public void FloodFill_CollectsOnlyTheConnectedRegion()
        {
            var grid = new TestGrid(
                "..#..",
                "..#..",
                "#####",
                ".....");
            var cells = new List<Vector2Int>();

            Assert.That(new GridFloodFill().Fill(grid, new Vector2Int(0, 3), cells), Is.EqualTo(4));
            Assert.That(cells, Has.All.Matches<Vector2Int>(cell => cell.x <= 1 && cell.y >= 2));
        }

        [Test]
        public void SpatialHash_QueryFindsItemsWithinRadius_AcrossCells()
        {
            var hash = new SpatialHash<string>(1f);
            hash.Add("near", new Vector3(0.5f, 0f, 0f));
            hash.Add("edge", new Vector3(2f, 0f, 0f));
            hash.Add("far", new Vector3(5f, 0f, 0f));
            var results = new List<string>();

            hash.Query(Vector3.zero, 2f, results);
            Assert.That(results, Is.EquivalentTo(new[] { "near", "edge" }));

            hash.Move("far", new Vector3(-1f, 0f, 0f));
            hash.Remove("edge");
            hash.Query(Vector3.zero, 2f, results);
            Assert.That(results, Is.EquivalentTo(new[] { "near", "far" }));
        }

        [Test]
        public void SpatialHash_AddingTheSameItemTwice_Throws()
        {
            var hash = new SpatialHash<int>(1f);
            hash.Add(1, Vector3.zero);

            Assert.Throws<ArgumentException>(() => hash.Add(1, Vector3.one));
        }

        [Test]
        public void SpatialHash_Query_DoesNotAllocate()
        {
            var hash = new SpatialHash<int>(1f);
            for (var i = 0; i < 100; i++) hash.Add(i, new Vector3(i % 10, 0f, i / 10));
            var results = new List<int>(100);
            hash.Query(new Vector3(5f, 0f, 5f), 3f, results);

            Assert.That(() => hash.Query(new Vector3(5f, 0f, 5f), 3f, results), Is.Not.AllocatingGCMemory());
        }

        [Test]
        public void PoissonDiskSampling_RespectsMinimumDistance_AndStaysInArea()
        {
            var area = new Rect(-5f, 2f, 20f, 10f);
            var points = new List<Vector2>();
            PoissonDiskSampling.Sample(area, 1f, new Random(5), points);

            Assert.That(points.Count, Is.GreaterThan(80));
            Assert.That(points, Has.All.Matches<Vector2>(point => area.Contains(point)));
            for (var i = 0; i < points.Count; i++)
            for (var j = i + 1; j < points.Count; j++)
                Assert.That(Vector2.Distance(points[i], points[j]), Is.GreaterThanOrEqualTo(1f - 1e-4f));
        }
    }
}
