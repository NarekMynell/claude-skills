using System;
using System.Collections.Generic;
using UnityEngine;

namespace Company.Product.Core.Algorithms
{
    // Collects the walkable cells connected to a start cell through its four straight neighbours.
    public sealed class GridFloodFill
    {
        private readonly Queue<int> _queue = new Queue<int>(64);
        private int[] _visited = Array.Empty<int>();
        private int _stamp;

        public int Fill(IWalkableGrid grid, Vector2Int start, List<Vector2Int> cells)
        {
            if (grid == null) throw new ArgumentNullException(nameof(grid));
            if (cells == null) throw new ArgumentNullException(nameof(cells));

            cells.Clear();
            var width = grid.Width;
            var height = grid.Height;
            if (!IsOpen(grid, start.x, start.y)) return 0;

            Prepare(width * height);
            Enqueue(start.y * width + start.x);
            while (_queue.Count > 0)
            {
                var index = _queue.Dequeue();
                var x = index % width;
                var y = index / width;
                cells.Add(new Vector2Int(x, y));

                if (IsOpen(grid, x + 1, y)) Enqueue(index + 1);
                if (IsOpen(grid, x - 1, y)) Enqueue(index - 1);
                if (IsOpen(grid, x, y + 1)) Enqueue(index + width);
                if (IsOpen(grid, x, y - 1)) Enqueue(index - width);
            }

            return cells.Count;
        }

        private void Enqueue(int index)
        {
            if (_visited[index] == _stamp) return;

            _visited[index] = _stamp;
            _queue.Enqueue(index);
        }

        private void Prepare(int cellCount)
        {
            if (_visited.Length < cellCount)
            {
                _visited = new int[cellCount];
                _stamp = 0;
            }

            if (_stamp == int.MaxValue)
            {
                Array.Clear(_visited, 0, _visited.Length);
                _stamp = 0;
            }

            _stamp++;
            _queue.Clear();
        }

        private static bool IsOpen(IWalkableGrid grid, int x, int y) =>
            x >= 0 && y >= 0 && x < grid.Width && y < grid.Height && grid.IsWalkable(x, y);
    }
}
