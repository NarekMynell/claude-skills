using System;
using System.Collections.Generic;

namespace Company.Product.Core.Collections
{
    // Binary min-heap keyed by priority. Equal priorities dequeue in no particular order.
    public sealed class MinHeap<TElement, TPriority>
    {
        private readonly IComparer<TPriority> _comparer;
        private (TElement Element, TPriority Priority)[] _nodes;

        public MinHeap(int capacity = 16, IComparer<TPriority> comparer = null)
        {
            if (capacity < 1) throw new ArgumentOutOfRangeException(nameof(capacity));

            _nodes = new (TElement, TPriority)[capacity];
            _comparer = comparer ?? Comparer<TPriority>.Default;
        }

        public int Count { get; private set; }

        public void Enqueue(TElement element, TPriority priority)
        {
            if (Count == _nodes.Length) Array.Resize(ref _nodes, _nodes.Length * 2);

            var index = Count++;
            while (index > 0)
            {
                var parent = (index - 1) >> 1;
                if (_comparer.Compare(priority, _nodes[parent].Priority) >= 0) break;

                _nodes[index] = _nodes[parent];
                index = parent;
            }

            _nodes[index] = (element, priority);
        }

        public TElement Dequeue() =>
            TryDequeue(out var element, out _) ? element : throw new InvalidOperationException("The heap is empty.");

        public bool TryDequeue(out TElement element, out TPriority priority)
        {
            if (Count == 0)
            {
                element = default;
                priority = default;
                return false;
            }

            (element, priority) = _nodes[0];
            var last = _nodes[--Count];
            _nodes[Count] = default;
            if (Count > 0) SiftDown(last);
            return true;
        }

        public bool TryPeek(out TElement element, out TPriority priority)
        {
            if (Count == 0)
            {
                element = default;
                priority = default;
                return false;
            }

            (element, priority) = _nodes[0];
            return true;
        }

        public void Clear()
        {
            Array.Clear(_nodes, 0, Count);
            Count = 0;
        }

        private void SiftDown((TElement Element, TPriority Priority) node)
        {
            var index = 0;
            var half = Count >> 1;
            while (index < half)
            {
                var child = (index << 1) + 1;
                var right = child + 1;
                if (right < Count && _comparer.Compare(_nodes[right].Priority, _nodes[child].Priority) < 0) child = right;
                if (_comparer.Compare(node.Priority, _nodes[child].Priority) <= 0) break;

                _nodes[index] = _nodes[child];
                index = child;
            }

            _nodes[index] = node;
        }
    }
}
