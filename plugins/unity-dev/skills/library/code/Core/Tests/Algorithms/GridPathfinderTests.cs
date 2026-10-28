using System.Collections.Generic;
using Company.Product.Core.Algorithms;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;

namespace Company.Product.Core.Tests.Algorithms
{
    public sealed class GridPathfinderTests
    {
        private readonly List<Vector2Int> _path = new List<Vector2Int>();

        [Test]
        public void OpenGrid_StraightPath_HasOneCellPerStep()
        {
            var grid = new TestGrid(".....");

            Assert.That(new GridPathfinder().TryFindPath(grid, new Vector2Int(0, 0), new Vector2Int(4, 0), _path), Is.True);
            Assert.That(_path.Count, Is.EqualTo(5));
            Assert.That(_path[0], Is.EqualTo(new Vector2Int(0, 0)));
            Assert.That(_path[4], Is.EqualTo(new Vector2Int(4, 0)));
        }

        [Test]
        public void Wall_PathGoesAroundIt_AndEveryStepIsAdjacent()
        {
            var grid = new TestGrid(
                ".....",
                ".###.",
                ".....");
            var pathfinder = new GridPathfinder(allowDiagonals: false);

            Assert.That(pathfinder.TryFindPath(grid, new Vector2Int(0, 1), new Vector2Int(4, 1), _path), Is.True);
            Assert.That(_path.Count, Is.EqualTo(7));
            for (var i = 1; i < _path.Count; i++)
                Assert.That(Mathf.Abs(_path[i].x - _path[i - 1].x) + Mathf.Abs(_path[i].y - _path[i - 1].y), Is.EqualTo(1));
        }

        [Test]
        public void EnclosedGoal_HasNoPath()
        {
            var grid = new TestGrid(
                "..#.",
                "..#.",
                "..#.");

            Assert.That(new GridPathfinder().TryFindPath(grid, new Vector2Int(0, 0), new Vector2Int(3, 0), _path), Is.False);
            Assert.That(_path, Is.Empty);
        }

        [Test]
        public void Diagonal_NeverCutsACorner()
        {
            var grid = new TestGrid(
                "#.",
                "..");

            Assert.That(new GridPathfinder().TryFindPath(grid, new Vector2Int(0, 0), new Vector2Int(1, 1), _path), Is.True);
            Assert.That(_path.Count, Is.EqualTo(3));
            Assert.That(_path[1], Is.EqualTo(new Vector2Int(1, 0)));
        }

        [Test]
        public void Diagonal_IsUsedWhenBothSidesAreOpen()
        {
            var grid = new TestGrid(
                "..",
                "..");

            Assert.That(new GridPathfinder().TryFindPath(grid, new Vector2Int(0, 0), new Vector2Int(1, 1), _path), Is.True);
            Assert.That(_path.Count, Is.EqualTo(2));
        }

        [Test]
        public void RepeatedSearches_DoNotAllocate()
        {
            var grid = new TestGrid(
                "..........",
                ".########.",
                "..........",
                ".########.",
                "..........");
            var pathfinder = new GridPathfinder();
            var start = new Vector2Int(0, 0);
            var goal = new Vector2Int(9, 4);
            pathfinder.TryFindPath(grid, start, goal, _path);

            Assert.That(() => { pathfinder.TryFindPath(grid, start, goal, _path); }, Is.Not.AllocatingGCMemory());
        }
    }
}
