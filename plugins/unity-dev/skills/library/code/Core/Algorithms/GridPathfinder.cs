using System;
using System.Collections.Generic;
using Company.Product.Core.Collections;
using UnityEngine;

namespace Company.Product.Core.Algorithms
{
    // A* on a grid. Reuses its buffers, so repeated searches on the same grid size don't allocate.
    public sealed class GridPathfinder
    {
        private const float StraightCost = 1f;
        private const float DiagonalCost = 1.41421356f;

        private static readonly Vector2Int[] StraightSteps = { new Vector2Int(1, 0), new Vector2Int(-1, 0), new Vector2Int(0, 1), new Vector2Int(0, -1) };
        private static readonly Vector2Int[] DiagonalSteps = { new Vector2Int(1, 1), new Vector2Int(1, -1), new Vector2Int(-1, 1), new Vector2Int(-1, -1) };

        private MinHeap<int, float> _open = new MinHeap<int, float>(64);
        private float[] _costs = Array.Empty<float>();
        private int[] _parents = Array.Empty<int>();
        private int[] _visited = Array.Empty<int>();
        private int[] _closed = Array.Empty<int>();
        private int _stamp;

        public GridPathfinder(bool allowDiagonals = true) => AllowDiagonals = allowDiagonals;

        // Diagonal moves never cut corners: both adjacent straight cells must be walkable.
        public bool AllowDiagonals { get; }

        public bool TryFindPath(IWalkableGrid grid, Vector2Int start, Vector2Int goal, List<Vector2Int> path)
        {
            if (grid == null) throw new ArgumentNullException(nameof(grid));
            if (path == null) throw new ArgumentNullException(nameof(path));

            path.Clear();
            if (!IsOpen(grid, start.x, start.y) || !IsOpen(grid, goal.x, goal.y)) return false;

            var width = grid.Width;
            Prepare(width * grid.Height);
            var startIndex = start.y * width + start.x;
            var goalIndex = goal.y * width + goal.x;

            Visit(startIndex, 0f, -1);
            _open.Enqueue(startIndex, Heuristic(start.x, start.y, goal));

            while (_open.TryDequeue(out var current, out _))
            {
                if (current == goalIndex)
                {
                    BuildPath(current, width, path);
                    return true;
                }

                if (_closed[current] == _stamp) continue;

                _closed[current] = _stamp;
                var x = current % width;
                var y = current / width;
                Expand(grid, x, y, current, goal, StraightSteps, StraightCost);
                if (AllowDiagonals) Expand(grid, x, y, current, goal, DiagonalSteps, DiagonalCost);
            }

            return false;
        }

        private void Expand(IWalkableGrid grid, int x, int y, int current, Vector2Int goal, Vector2Int[] steps, float stepCost)
        {
            var width = grid.Width;
            for (var i = 0; i < steps.Length; i++)
            {
                var nx = x + steps[i].x;
                var ny = y + steps[i].y;
                if (!IsOpen(grid, nx, ny)) continue;
                if (steps[i].x != 0 && steps[i].y != 0 && (!IsOpen(grid, nx, y) || !IsOpen(grid, x, ny))) continue;

                var next = ny * width + nx;
                if (_closed[next] == _stamp) continue;

                var cost = _costs[current] + stepCost;
                if (_visited[next] == _stamp && cost >= _costs[next]) continue;

                Visit(next, cost, current);
                _open.Enqueue(next, cost + Heuristic(nx, ny, goal));
            }
        }

        private float Heuristic(int x, int y, Vector2Int goal)
        {
            var dx = Mathf.Abs(goal.x - x);
            var dy = Mathf.Abs(goal.y - y);
            return AllowDiagonals
                ? StraightCost * (dx + dy) + (DiagonalCost - 2f * StraightCost) * Mathf.Min(dx, dy)
                : StraightCost * (dx + dy);
        }

        private void Visit(int index, float cost, int parent)
        {
            _visited[index] = _stamp;
            _costs[index] = cost;
            _parents[index] = parent;
        }

        private void BuildPath(int goalIndex, int width, List<Vector2Int> path)
        {
            for (var index = goalIndex; index >= 0; index = _parents[index])
                path.Add(new Vector2Int(index % width, index / width));

            path.Reverse();
        }

        private void Prepare(int cellCount)
        {
            if (_costs.Length < cellCount)
            {
                _costs = new float[cellCount];
                _parents = new int[cellCount];
                _visited = new int[cellCount];
                _closed = new int[cellCount];
                // Sized with the grid, so a later, longer search on it doesn't grow the queue.
                _open = new MinHeap<int, float>(cellCount);
                _stamp = 0;
            }

            if (_stamp == int.MaxValue)
            {
                Array.Clear(_visited, 0, _visited.Length);
                Array.Clear(_closed, 0, _closed.Length);
                _stamp = 0;
            }

            _stamp++;
            _open.Clear();
        }

        private static bool IsOpen(IWalkableGrid grid, int x, int y) =>
            x >= 0 && y >= 0 && x < grid.Width && y < grid.Height && grid.IsWalkable(x, y);
    }
}
