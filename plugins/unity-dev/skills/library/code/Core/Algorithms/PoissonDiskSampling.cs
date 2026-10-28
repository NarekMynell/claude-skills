using System;
using System.Collections.Generic;
using Company.Product.Core.Extensions;
using UnityEngine;
using Random = System.Random;

namespace Company.Product.Core.Algorithms
{
    // Bridson's algorithm: evenly spread random points, no two closer than minDistance.
    // Allocates its working grid per call: use it while generating content, not every frame.
    public static class PoissonDiskSampling
    {
        public static void Sample(Rect area, float minDistance, Random random, List<Vector2> points, int attemptsPerPoint = 30)
        {
            if (!(minDistance > 0f)) throw new ArgumentOutOfRangeException(nameof(minDistance));
            if (area.width <= 0f || area.height <= 0f) throw new ArgumentException("The area must have a positive size.", nameof(area));
            if (random == null) throw new ArgumentNullException(nameof(random));
            if (points == null) throw new ArgumentNullException(nameof(points));
            if (attemptsPerPoint < 1) throw new ArgumentOutOfRangeException(nameof(attemptsPerPoint));

            points.Clear();
            var cellSize = minDistance / Mathf.Sqrt(2f);
            var columns = Mathf.CeilToInt(area.width / cellSize);
            var rows = Mathf.CeilToInt(area.height / cellSize);
            var grid = new int[columns * rows];
            for (var i = 0; i < grid.Length; i++) grid[i] = -1;

            var active = new List<int>();
            var squaredMinDistance = minDistance * minDistance;

            Add(new Vector2(area.xMin + (float)random.NextDouble() * area.width, area.yMin + (float)random.NextDouble() * area.height));
            while (active.Count > 0)
            {
                var activeIndex = random.Next(active.Count);
                var origin = points[active[activeIndex]];
                var placed = false;
                for (var attempt = 0; attempt < attemptsPerPoint; attempt++)
                {
                    var angle = random.NextDouble() * Math.PI * 2.0;
                    var distance = minDistance * (1.0 + random.NextDouble());
                    var candidate = origin + new Vector2((float)(Math.Cos(angle) * distance), (float)(Math.Sin(angle) * distance));
                    if (!area.Contains(candidate) || !IsFarEnough(candidate)) continue;

                    Add(candidate);
                    placed = true;
                    break;
                }

                if (!placed) active.SwapRemoveAt(activeIndex);
            }

            void Add(Vector2 point)
            {
                points.Add(point);
                active.Add(points.Count - 1);
                grid[CellIndex(point)] = points.Count - 1;
            }

            bool IsFarEnough(Vector2 candidate)
            {
                var column = Column(candidate);
                var row = Row(candidate);
                for (var y = Mathf.Max(row - 2, 0); y <= Mathf.Min(row + 2, rows - 1); y++)
                for (var x = Mathf.Max(column - 2, 0); x <= Mathf.Min(column + 2, columns - 1); x++)
                {
                    var neighbour = grid[y * columns + x];
                    if (neighbour >= 0 && (points[neighbour] - candidate).sqrMagnitude < squaredMinDistance) return false;
                }

                return true;
            }

            int Column(Vector2 point) => Mathf.Min((int)((point.x - area.xMin) / cellSize), columns - 1);

            int Row(Vector2 point) => Mathf.Min((int)((point.y - area.yMin) / cellSize), rows - 1);

            int CellIndex(Vector2 point) => Row(point) * columns + Column(point);
        }
    }
}
