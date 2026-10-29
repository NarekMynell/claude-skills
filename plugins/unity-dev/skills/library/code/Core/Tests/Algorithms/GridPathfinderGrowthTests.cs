using System.Collections.Generic;
using Company.Product.Core.Algorithms;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools.Constraints;
using Is = UnityEngine.TestTools.Constraints.Is;

namespace Company.Product.Core.Tests.Algorithms
{
    public sealed class GridPathfinderGrowthTests
    {
        private sealed class OpenGrid : IWalkableGrid
        {
            public OpenGrid(int width, int height)
            {
                Width = width;
                Height = height;
            }

            public int Width { get; }

            public int Height { get; }

            public bool IsWalkable(int x, int y) => true;
        }

        // README: "no allocations after the first search on a grid size".
        [Test]
        public void LongerSearch_AfterAShortOneOnTheSameGrid_DoesNotAllocate()
        {
            var grid = new OpenGrid(64, 64);
            var path = new List<Vector2Int>(256);
            var pathfinder = new GridPathfinder();
            pathfinder.TryFindPath(grid, new Vector2Int(0, 0), new Vector2Int(1, 0), path);

            Assert.That(() => { pathfinder.TryFindPath(grid, new Vector2Int(0, 63), new Vector2Int(63, 0), path); }, Is.Not.AllocatingGCMemory());
        }
    }
}
