using System;
using System.Collections.Generic;
using Company.Product.Core.Extensions;
using UnityEngine;

namespace Company.Product.Core.Algorithms
{
    // Uniform grid for neighbour queries. A query costs one lookup per cell its sphere covers,
    // so pick a cell size close to the usual query radius.
    public sealed class SpatialHash<T>
    {
        private readonly float _inverseCellSize;
        private readonly Dictionary<T, Vector3> _positions;
        private readonly Dictionary<Vector3Int, List<T>> _cells = new Dictionary<Vector3Int, List<T>>();
        private readonly Stack<List<T>> _freeLists = new Stack<List<T>>();

        public SpatialHash(float cellSize, IEqualityComparer<T> comparer = null)
        {
            if (!(cellSize > 0f) || float.IsInfinity(cellSize)) throw new ArgumentOutOfRangeException(nameof(cellSize));

            CellSize = cellSize;
            _inverseCellSize = 1f / cellSize;
            _positions = new Dictionary<T, Vector3>(comparer ?? EqualityComparer<T>.Default);
        }

        public float CellSize { get; }

        public int Count => _positions.Count;

        public bool Contains(T item) => _positions.ContainsKey(item);

        public void Add(T item, Vector3 position)
        {
            _positions.Add(item, position);
            GetOrCreateCell(CellOf(position)).Add(item);
        }

        public bool Remove(T item)
        {
            if (!_positions.TryGetValue(item, out var position)) return false;

            _positions.Remove(item);
            RemoveFromCell(CellOf(position), item);
            return true;
        }

        public void Move(T item, Vector3 position)
        {
            if (!_positions.TryGetValue(item, out var previous)) throw new ArgumentException("The item isn't in the hash.", nameof(item));

            _positions[item] = position;
            var from = CellOf(previous);
            var to = CellOf(position);
            if (from == to) return;

            RemoveFromCell(from, item);
            GetOrCreateCell(to).Add(item);
        }

        public void Query(Vector3 center, float radius, List<T> results)
        {
            if (results == null) throw new ArgumentNullException(nameof(results));
            if (radius < 0f) throw new ArgumentOutOfRangeException(nameof(radius));

            results.Clear();
            var squaredRadius = radius * radius;
            var extent = new Vector3(radius, radius, radius);
            var min = CellOf(center - extent);
            var max = CellOf(center + extent);
            for (var x = min.x; x <= max.x; x++)
            for (var y = min.y; y <= max.y; y++)
            for (var z = min.z; z <= max.z; z++)
            {
                if (!_cells.TryGetValue(new Vector3Int(x, y, z), out var cell)) continue;

                for (var i = 0; i < cell.Count; i++)
                {
                    var item = cell[i];
                    if ((_positions[item] - center).sqrMagnitude <= squaredRadius) results.Add(item);
                }
            }
        }

        public void Clear()
        {
            foreach (var cell in _cells.Values)
            {
                cell.Clear();
                _freeLists.Push(cell);
            }

            _cells.Clear();
            _positions.Clear();
        }

        private Vector3Int CellOf(Vector3 position) => new Vector3Int(
            Mathf.FloorToInt(position.x * _inverseCellSize),
            Mathf.FloorToInt(position.y * _inverseCellSize),
            Mathf.FloorToInt(position.z * _inverseCellSize));

        private List<T> GetOrCreateCell(Vector3Int key)
        {
            if (_cells.TryGetValue(key, out var cell)) return cell;

            cell = _freeLists.Count > 0 ? _freeLists.Pop() : new List<T>(4);
            _cells.Add(key, cell);
            return cell;
        }

        private void RemoveFromCell(Vector3Int key, T item)
        {
            var cell = _cells[key];
            var comparer = _positions.Comparer;
            for (var i = 0; i < cell.Count; i++)
            {
                if (!comparer.Equals(cell[i], item)) continue;

                cell.SwapRemoveAt(i);
                break;
            }

            if (cell.Count > 0) return;

            _cells.Remove(key);
            _freeLists.Push(cell);
        }
    }
}
